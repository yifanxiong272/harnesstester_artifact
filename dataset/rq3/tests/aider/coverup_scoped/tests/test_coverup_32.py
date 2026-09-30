# file: aider/coders/search_replace.py:485-521
# asked: {"lines": [486, 488, 489, 491, 493, 494, 495, 496, 499, 500, 501, 502, 505, 508, 509, 510, 513, 514, 515, 517, 519, 521], "branches": []}
# gained: {"lines": [486, 488, 489, 491, 493, 494, 495, 496, 499, 500, 501, 502, 505, 508, 509, 510, 513, 514, 515, 517, 519, 521], "branches": []}

import tempfile
import os
from types import SimpleNamespace
import contextlib
import pathlib
import uuid

import pytest

from aider.coders import search_replace as sr_mod


class FakeRepo:
    def __init__(self, dname):
        # working directory path (string)
        self.dname = dname
        self.commits = {}  # hash -> {'content': str, 'parent': hash or None}
        self._counter = 0
        self.staged_path = None
        self.staged_content = None
        # head will be a SimpleNamespace(commit=SimpleNamespace(hexsha=hash))
        self.head = SimpleNamespace(commit=SimpleNamespace(hexsha=None))
        # expose git commands object
        self.git = self.GitCommands(self)

    def _new_hash(self):
        # deterministic-ish unique hash for tests
        self._counter += 1
        return f"fakehash{self._counter}"

    class GitCommands:
        def __init__(self, repo):
            self._repo = repo

        def add(self, path):
            # read file content and stage it
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self._repo.staged_path = path
            self._repo.staged_content = content

        def commit(self, *args, **kwargs):
            # create a new commit from staged content
            if self._repo.staged_content is None:
                raise RuntimeError("nothing staged")
            parent = self._repo.head.commit.hexsha
            h = self._repo._new_hash()
            self._repo.commits[h] = {"content": self._repo.staged_content, "parent": parent}
            # update head
            self._repo.head = SimpleNamespace(commit=SimpleNamespace(hexsha=h))
            # clear staging
            self._repo.staged_path = None
            self._repo.staged_content = None

        def checkout(self, hexsha):
            # set head to given commit and write its content to working file
            if hexsha not in self._repo.commits:
                raise RuntimeError("unknown commit")
            content = self._repo.commits[hexsha]["content"]
            # write content to the same file path that was used previously.
            # If no staged_path ever set, attempt to find a file in repo dir.
            if self._repo.staged_path:
                path = self._repo.staged_path
            else:
                # try to find a file named 'file.txt' in repo dir
                path = os.path.join(self._repo.dname, "file.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self._repo.head = SimpleNamespace(commit=SimpleNamespace(hexsha=hexsha))

        def cherry_pick(self, replace_hash, flag):
            # Simulate minimal cherry-pick: apply diff between parent(replace) -> replace
            # onto current head. If base content not present in current head, raise git error.
            repo = self._repo
            if replace_hash not in repo.commits:
                raise RuntimeError("unknown replace hash")
            replace_commit = repo.commits[replace_hash]
            parent_hash = replace_commit["parent"]
            if parent_hash is None:
                base_content = ""
            else:
                base_content = repo.commits[parent_hash]["content"]
            replace_content = replace_commit["content"]
            current_head_hash = repo.head.commit.hexsha
            if current_head_hash is None:
                current_content = ""
            else:
                current_content = repo.commits[current_head_hash]["content"]

            # For simplicity, treat the "diff" as replacing the entire base_content substring
            # with replace_content inside current_content. If base_content is not a substring,
            # then treat as conflict and raise git.exc.GitError.
            if base_content == "":
                # No base; just set to replace_content
                new_content = replace_content
            else:
                if base_content not in current_content:
                    # simulate a merge conflict by raising the GitError from the real git module
                    raise sr_mod.git.exc.GitError("simulation: conflict")
                new_content = current_content.replace(base_content, replace_content)

            # write new content to working file
            path = os.path.join(repo.dname, "file.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            # create a new commit representing the cherry-pick result
            new_hash = repo._new_hash()
            repo.commits[new_hash] = {"content": new_content, "parent": current_head_hash}
            repo.head = SimpleNamespace(commit=SimpleNamespace(hexsha=new_hash))


@contextlib.contextmanager
def fake_git_temporary_directory():
    td = tempfile.TemporaryDirectory()
    try:
        yield td.name
    finally:
        td.cleanup()


def setup_monkeypatch_for_fake_repo(monkeypatch):
    # Patch GitTemporaryDirectory in module to our fake context manager
    monkeypatch.setattr(sr_mod, "GitTemporaryDirectory", fake_git_temporary_directory)
    # Patch git.Repo in that module to our FakeRepo
    monkeypatch.setattr(sr_mod.git, "Repo", FakeRepo)


def test_git_cherry_pick_success(monkeypatch):
    setup_monkeypatch_for_fake_repo(monkeypatch)

    # Compose texts where search_text is uniquely present inside original_text
    search_text = "SEARCH_MARKER\n"
    replace_text = "REPLACED_MARKER\n"
    original_text = "before\nSEARCH_MARKER\nafter\n"

    result = sr_mod.git_cherry_pick_sr_onto_so((search_text, replace_text, original_text))
    # Expect the SEARCH_MARKER substring in original to be replaced by REPLACED_MARKER
    expected = original_text.replace(search_text, replace_text)
    assert result == expected

    # Also ensure that the file on disk inside the temporary repo was updated to expected
    # We can recreate the temp dir by invoking GitTemporaryDirectory context manager to find it?
    # Instead, we know the fake repo cleaned up; but function wrote the file inside temp dir and then returned.
    # To double-check persistent behavior, run function again with same inputs to ensure deterministic result.
    result2 = sr_mod.git_cherry_pick_sr_onto_so((search_text, replace_text, original_text))
    assert result2 == expected


def test_git_cherry_pick_conflict_returns_none(monkeypatch):
    setup_monkeypatch_for_fake_repo(monkeypatch)

    # Compose texts where search_text does NOT appear in original_text -> conflict simulated
    search_text = "UNIQUE_SEARCH\n"
    replace_text = "NEW_VALUE\n"
    original_text = "completely different content\n"

    result = sr_mod.git_cherry_pick_sr_onto_so((search_text, replace_text, original_text))
    # Function should catch the simulated git.exc.GitError and return None
    assert result is None
