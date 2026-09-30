# file: aider/coders/search_replace.py:448-482
# asked: {"lines": [449, 451, 452, 454, 457, 458, 459, 460, 462, 463, 464, 466, 467, 468, 469, 472, 475, 476, 477, 479, 481, 482], "branches": []}
# gained: {"lines": [449, 451, 452, 454, 457, 458, 459, 460, 462, 463, 464, 466, 467, 468, 469, 472, 475, 476, 477, 479, 481, 482], "branches": []}

import tempfile
from pathlib import Path

import git
import pytest

import aider.coders.search_replace as sr


class SimpleGitTempDir:
    """
    Context manager that creates a temporary directory and returns its path.
    Used to replace aider.utils.GitTemporaryDirectory in tests.
    """
    def __enter__(self):
        self._td = tempfile.TemporaryDirectory()
        return self._td.name

    def __exit__(self, exc_type, exc, tb):
        self._td.cleanup()


class FakeCommit:
    def __init__(self, hexsha):
        self.hexsha = hexsha


class FakeHead:
    def __init__(self, commit):
        self.commit = commit


class FakeRepoSuccess:
    """
    Fake git.Repo that simulates commits by storing the file content at each commit.
    It supports add, commit, checkout, and cherry_pick in a deterministic way.
    """
    def __init__(self, dname):
        self._dname = dname
        self._commit_count = 0
        self._commits = {}  # hexsha -> content
        # initialize head to an empty commit
        self.head = FakeHead(FakeCommit(""))

        # Provide a .git namespace with methods used by the target function
        self.git = self  # methods implemented on this object

    def add(self, path):
        # noop for simulation
        return

    def commit(self, *args, **kwargs):
        # create a new fake commit capturing current file content
        self._commit_count += 1
        sha = f"commit{self._commit_count}"
        fname = Path(self._dname) / "file.txt"
        # read current file content (the function under test writes files directly)
        try:
            content = fname.read_text()
        except FileNotFoundError:
            content = ""
        self._commits[sha] = content
        self.head.commit.hexsha = sha
        return

    def checkout(self, rev):
        # when checking out a revision, restore the file to the stored commit content
        fname = Path(self._dname) / "file.txt"
        content = self._commits.get(rev, "")
        fname.write_text(content)
        return

    def cherry_pick(self, rev, *args, **kwargs):
        # simulate a successful cherry-pick by applying the commit content onto the working file
        fname = Path(self._dname) / "file.txt"
        content = self._commits.get(rev)
        if content is None:
            # if rev unknown, simulate GitError
            raise git.exc.GitError("unknown commit")
        # apply the content (simulate a successful cherry-pick)
        fname.write_text(content)
        # create a new head commit to reflect the cherry-pick application
        self._commit_count += 1
        sha = f"commit{self._commit_count}"
        self._commits[sha] = content
        self.head.commit.hexsha = sha
        return


class FakeRepoConflict(FakeRepoSuccess):
    # Inherit to reuse commit bookkeeping, but override cherry_pick to raise
    def cherry_pick(self, rev, *args, **kwargs):
        raise git.exc.GitError("simulated conflict")


def test_git_cherry_pick_success(monkeypatch):
    # Use the simple temp dir manager
    monkeypatch.setattr(sr, "GitTemporaryDirectory", SimpleGitTempDir)
    # Replace git.Repo with our fake that simulates success
    monkeypatch.setattr(sr.git, "Repo", FakeRepoSuccess)

    search_text = "search\n"
    replace_text = "replace\n"
    original_text = "original\n"

    res = sr.git_cherry_pick_osr_onto_o((search_text, replace_text, original_text))

    # On simulated success, the returned new_text should equal replace_text
    assert res == replace_text

    # Additionally, ensure that the fake repo recorded commits for original, search, and replace
    # We can recreate a FakeRepoSuccess to inspect behavior indirectly by running the function again
    # but here we assert the function returned the expected applied content which is sufficient.


def test_git_cherry_pick_conflict_returns_none(monkeypatch):
    # Use the simple temp dir manager
    monkeypatch.setattr(sr, "GitTemporaryDirectory", SimpleGitTempDir)
    # Replace git.Repo with our fake that simulates a cherry-pick conflict
    monkeypatch.setattr(sr.git, "Repo", FakeRepoConflict)

    search_text = "search\n"
    replace_text = "replace\n"
    original_text = "original\n"

    res = sr.git_cherry_pick_osr_onto_o((search_text, replace_text, original_text))

    # Because cherry_pick raises GitError, the function should catch it and return None.
    assert res is None
