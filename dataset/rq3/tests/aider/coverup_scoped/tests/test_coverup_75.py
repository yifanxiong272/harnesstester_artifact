# file: aider/repo.py:131-317
# asked: {"lines": [202, 270, 273, 285, 286], "branches": [[201, 202], [214, 216], [250, 252], [269, 270], [272, 273]]}
# gained: {"lines": [202, 270, 273, 285, 286], "branches": [[201, 202], [269, 270], [272, 273]]}

import os
import types
import pytest

import aider.repo as repo_mod
from aider.repo import GitRepo


class DummyIO:
    def __init__(self):
        self.errors = []
        self.outputs = []

    def tool_error(self, msg):
        self.errors.append(msg)

    def tool_output(self, msg, **kwargs):
        self.outputs.append((msg, kwargs))


class DummyGit:
    def __init__(self, add_raises=None):
        self._add_raises = add_raises
        self.committed_cmd = None

    def add(self, fname):
        if self._add_raises:
            raise self._add_raises
        return None

    def commit(self, cmd):
        self.committed_cmd = cmd
        return None

    def config(self, *args):
        # Simulate returning a username
        return "Original User"


class DummyRepo:
    def __init__(self, git_obj, is_dirty=True):
        self.git = git_obj
        self._is_dirty = is_dirty
        self.working_tree_dir = "/fake/root"

    def is_dirty(self):
        return self._is_dirty


class DummyCoderArgs:
    def __init__(
        self,
        attribute_author=None,
        attribute_committer=None,
        attribute_commit_message_author=False,
        attribute_commit_message_committer=False,
        attribute_co_authored_by=False,
    ):
        self.attribute_author = attribute_author
        self.attribute_committer = attribute_committer
        self.attribute_commit_message_author = attribute_commit_message_author
        self.attribute_commit_message_committer = attribute_commit_message_committer
        self.attribute_co_authored_by = attribute_co_authored_by


class DummyModel:
    def __init__(self, name):
        self.name = name


class DummyCoder:
    def __init__(self, commit_language=None, args=None, main_model=None):
        self.commit_language = commit_language
        self._get_user_language_called = False
        self.args = args
        self.main_model = main_model

    def get_user_language(self):
        self._get_user_language_called = True
        return "en"


def make_repo_instance():
    # Create an "empty" GitRepo instance without running __init__
    r = object.__new__(GitRepo)
    return r


def test_commit_returns_none_when_no_fnames_and_not_dirty():
    io = DummyIO()
    fake_git = DummyGit()
    fake_repo = DummyRepo(fake_git, is_dirty=False)

    r = make_repo_instance()
    # Set only what's needed for this test
    r.repo = fake_repo
    r.io = io

    # Should return None when no fnames and repo is not dirty
    result = r.commit(fnames=None)
    assert result is None
    # Ensure no errors or outputs were produced
    assert io.errors == []
    assert io.outputs == []


def test_commit_handles_empty_message_prefix_and_coauthor_and_add_error(monkeypatch):
    io = DummyIO()
    # Make git.add raise a generic Exception so that the add-exception path is exercised
    dummy_git = DummyGit(add_raises=Exception("boom"))
    fake_repo = DummyRepo(dummy_git, is_dirty=True)

    # Create coder with args to drive various attribute flags and model name
    coder_args = DummyCoderArgs(
        attribute_author=None,  # implicit
        attribute_committer=False,  # to avoid set_git_env for committer
        attribute_commit_message_author=True,  # causes prefixing
        attribute_commit_message_committer=False,
        attribute_co_authored_by=True,  # causes trailer
    )
    coder = DummyCoder(commit_language=None, args=coder_args, main_model=DummyModel("mymodel"))

    # Create the GitRepo instance without running __init__
    r = make_repo_instance()
    r.repo = fake_repo
    r.io = io
    # Provide methods/attributes used by commit
    # get_diffs must return non-empty to proceed
    r.get_diffs = lambda fnames: ["diff"]
    # We'll replace get_commit_message to capture the user_language passed in
    captured = {}

    def fake_get_commit_message(diffs, context, user_language=None):
        captured["user_language"] = user_language
        # Return empty string so code sets "(no commit message provided)"
        return ""

    r.get_commit_message = fake_get_commit_message
    # get_head_commit_sha should return a fake hash
    r.get_head_commit_sha = lambda short=True: "abc123"
    # abs_root_path used when fnames provided; keep it simple
    r.abs_root_path = lambda p: str(p)
    # Set git_commit_verify True to avoid --no-verify being added
    r.git_commit_verify = True

    # Ensure ANY_GIT_ERROR will catch the Exception we raise in DummyGit.add
    # It must be a tuple of exception types for the except clause to accept it.
    monkeypatch.setattr(repo_mod, "ANY_GIT_ERROR", (Exception,))

    # Call commit with a filename list to hit the add() loop and its exception handling
    commit_result = r.commit(fnames=["file.txt"], context=None, message=None, aider_edits=True, coder=coder)

    # The returned commit message should be prefixed and defaulted
    expected_commit_message = "aider: (no commit message provided)"
    assert commit_result == ("abc123", expected_commit_message)
    # Ensure the add error was reported via io.tool_error
    assert any("Unable to add file.txt" in e for e in io.errors)
    # Ensure get_user_language was used (captured via fake_get_commit_message user_language)
    assert captured.get("user_language") == "en"
    # Ensure the co-authored-by trailer was included in the commit command used to commit
    assert dummy_git.committed_cmd is not None
    # The commit message passed to git.commit should include the trailer with model name
    found_trailer = any(
        "Co-authored-by: aider (mymodel) <aider@aider.chat>" in str(part)
        for part in dummy_git.committed_cmd
    )
    assert found_trailer, "Expected co-authored-by trailer with model name in commit command"
