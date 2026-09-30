# file: aider/coders/search_replace.py:485-521
# asked: {"lines": [486, 488, 489, 491, 493, 494, 495, 496, 499, 500, 501, 502, 505, 508, 509, 510, 513, 514, 515, 517, 519, 521], "branches": []}
# gained: {"lines": [486, 488, 489, 491, 493, 494, 495, 496, 499, 500, 501, 502, 505, 508, 509, 510, 513, 514, 515, 517, 519, 521], "branches": []}

import git
from pathlib import Path
import types
import pytest

from aider.coders import search_replace as sr_mod
from aider.coders.search_replace import git_cherry_pick_sr_onto_so


class _FakeHead:
    def __init__(self, hexsha):
        self.commit = types.SimpleNamespace(hexsha=hexsha)


def _make_fake_repo_class(tmp_path, conflict=False):
    """
    Returns a FakeRepo class bound to tmp_path. If conflict is True,
    its cherry_pick will raise git.exc.GitError to simulate conflicts.
    """
    class FakeRepo:
        def __init__(self, dname):
            # dname may be a string or Path - normalize to Path
            self.dname = Path(dname)
            self.filepath = self.dname / "file.txt"
            self._commits = {}  # hexsha -> content
            self._order = []
            self._counter = 0
            # head points to last commit if any, else to None-like
            self.head = _FakeHead(hexsha="")

            # expose a .git namespace with required methods
            self.git = types.SimpleNamespace(
                add=self._add,
                commit=self._commit,
                checkout=self._checkout,
                cherry_pick=self._cherry_pick,
            )

        def _add(self, *args, **kwargs):
            # no-op for our fake
            return

        def _commit(self, *args, **kwargs):
            # create a new commit from current file content
            self._counter += 1
            hexsha = f"commit{self._counter:08d}"
            try:
                content = self.filepath.read_text()
            except FileNotFoundError:
                content = ""
            self._commits[hexsha] = content
            self._order.append(hexsha)
            self.head = _FakeHead(hexsha=hexsha)
            return hexsha

        def _checkout(self, hexsha, *args, **kwargs):
            # set head to the commit matching hexsha if present
            if hexsha not in self._commits:
                # emulate git behavior of checkout to hash that doesn't exist:
                # raise git.exc.GitError
                raise git.exc.GitError(f"commit {hexsha} not found")
            self.head = _FakeHead(hexsha=hexsha)
            # write the checked-out file content to the working tree
            self.filepath.write_text(self._commits[hexsha])

        def _cherry_pick(self, commit_hash, *args, **kwargs):
            if conflict:
                # simulate merge conflict by raising GitError (or ODBError)
                raise git.exc.GitError("conflict")
            if commit_hash not in self._commits:
                raise git.exc.GitError(f"commit {commit_hash} not found")
            # apply the content of the commit onto the working tree (overwrite)
            content = self._commits[commit_hash]
            # write content to working file to emulate successful cherry-pick
            self.filepath.write_text(content)
            # and create a new commit representing the cherry-pick result
            self._counter += 1
            new_hex = f"commit{self._counter:08d}"
            self._commits[new_hex] = content
            self._order.append(new_hex)
            self.head = _FakeHead(hexsha=new_hex)
            return new_hex

    return FakeRepo


class _FakeGTD:
    """Context manager to replace GitTemporaryDirectory. Returns the provided path."""
    def __init__(self, path):
        self._path = Path(path)

    def __enter__(self):
        return str(self._path)

    def __exit__(self, exc_type, exc, tb):
        return False


def test_git_cherry_pick_success(monkeypatch, tmp_path):
    """
    Test the successful path where cherry-pick applies replace_text onto original,
    so the function returns the replace_text.
    """
    search_text = "AAA\n"
    replace_text = "BBB\n"
    original_text = "CCC\n"

    # Create the repo directory (GitTemporaryDirectory would have created it)
    # but function will write files there using Path(dname)/file.txt
    # tmp_path is used as our temporary repo directory.
    # Monkeypatch GitTemporaryDirectory in the module under test to yield tmp_path
    monkeypatch.setattr(sr_mod, "GitTemporaryDirectory", lambda: _FakeGTD(tmp_path))

    # Create a FakeRepo class bound to tmp_path with non-conflict behavior
    FakeRepo = _make_fake_repo_class(tmp_path, conflict=False)
    # Monkeypatch git.Repo used inside the function
    monkeypatch.setattr(git, "Repo", FakeRepo)

    # Run function under test
    result = git_cherry_pick_sr_onto_so((search_text, replace_text, original_text))

    # After successful cherry-pick, result should be replace_text
    assert result == replace_text

    # And file contents in tmp_path should be replace_text as well
    file_path = tmp_path / "file.txt"
    assert file_path.exists()
    assert file_path.read_text() == replace_text


def test_git_cherry_pick_conflict(monkeypatch, tmp_path):
    """
    Test the branch where cherry-pick raises git.exc.GitError (simulate conflict)
    and the function returns None without crashing.
    """
    search_text = "one\n"
    replace_text = "two\n"
    original_text = "orig\n"

    monkeypatch.setattr(sr_mod, "GitTemporaryDirectory", lambda: _FakeGTD(tmp_path))

    # FakeRepo that raises on cherry_pick
    FakeRepoConflict = _make_fake_repo_class(tmp_path, conflict=True)
    monkeypatch.setattr(git, "Repo", FakeRepoConflict)

    result = git_cherry_pick_sr_onto_so((search_text, replace_text, original_text))

    # On conflict, function returns None
    assert result is None

    # And the working file should remain as it was before attempted cherry-pick:
    # After the function makes the 'original' commit, the working tree contains original_text.
    file_path = tmp_path / "file.txt"
    # The file should exist (it was created and committed)
    assert file_path.exists()
    assert file_path.read_text() == original_text
