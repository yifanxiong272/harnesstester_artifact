import tempfile
from pathlib import Path
from types import SimpleNamespace
import pytest

from aider.coders import search_replace as sr


class _FakeGitExc:
    class GitError(Exception):
        pass

    class ODBError(Exception):
        pass


class FakeGitModule:
    """A minimal fake of the `git` module surface used by the function under test.

    - Repo(dname) -> FakeRepo instance
    - exc -> object containing GitError, ODBError
    """

    exc = _FakeGitExc
    # toggleable by tests
    raise_on_cherry_pick = False

    class Repo:
        def __init__(self, dname):
            # repository backs files under the working directory dname
            self.dname = dname
            self.git = SimpleNamespace()
            # storage of commit hash -> file content
            self._commits = {}
            self._counter = 1
            self._last_added = None
            # head.commit.hexsha
            self.head = SimpleNamespace(commit=SimpleNamespace(hexsha=None))

            # bind methods
            self.git.add = self._add
            self.git.commit = self._commit
            self.git.checkout = self._checkout

            # cherry_pick accepts (hash, "--minimal") per caller
            def _cherry_pick(h, *args, **kwargs):
                if FakeGitModule.raise_on_cherry_pick:
                    raise FakeGitModule.exc.GitError("simulated conflict")
                # apply the contents of the target commit onto the working file
                content = self._commits.get(h)
                if content is None:
                    # mimic Git behavior: if unknown hash, raise GitError
                    raise FakeGitModule.exc.GitError("unknown hash")
                # determine the single file path we previously added
                if not self._last_added:
                    raise FakeGitModule.exc.GitError("no file added")
                Path(self._last_added).write_text(content)
                # update head to a pseudo-new hash
                new_hash = f"cherry_{h}"
                self.head.commit.hexsha = new_hash

            self.git.cherry_pick = _cherry_pick

        def _add(self, path):
            # store last added path
            self._last_added = path

        def _commit(self, *args, **kwargs):
            # on commit, read the content of the last added file and create a hash
            if not self._last_added:
                raise FakeGitModule.exc.GitError("nothing to commit")
            p = Path(self._last_added)
            content = p.read_text()
            h = f"hash{self._counter}"
            self._counter += 1
            self._commits[h] = content
            self.head.commit.hexsha = h

        def _checkout(self, hexsha):
            # set the working file to the content stored at that hash
            content = self._commits.get(hexsha)
            if content is None:
                raise FakeGitModule.exc.GitError("unknown checkout")
            if not self._last_added:
                # if no file was added yet, try to find any file in the repo dir
                files = list(Path(self.dname).glob("**/*"))
                # choose file.txt fallback
                target = Path(self.dname) / "file.txt"
            else:
                target = Path(self._last_added)
            target.write_text(content)
            # update head
            self.head.commit.hexsha = hexsha


class TempDirCtx:
    """Context manager that yields a real temporary directory path string.

    This mirrors the interface of the real GitTemporaryDirectory used by the
    function under test (used as: with GitTemporaryDirectory() as dname:)
    """

    def __enter__(self):
        self._td = tempfile.TemporaryDirectory()
        return self._td.name

    def __exit__(self, exc_type, exc, tb):
        self._td.cleanup()
        return False


def _patch_fakes(monkeypatch, raise_on_cherry=False):
    """Helper to inject fakes into the module under test.

    - monkeypatch: pytest fixture
    - raise_on_cherry: when True, cherry_pick will raise GitError to simulate
      a conflict path.
    """
    FakeGitModule.raise_on_cherry_pick = raise_on_cherry
    # Patch the symbols where the function under test resolves them
    monkeypatch.setattr(sr, "GitTemporaryDirectory", TempDirCtx)
    monkeypatch.setattr(sr, "git", FakeGitModule)


def test_git_cherry_pick_success_round_077(monkeypatch):
    """Simulate a successful cherry-pick path.

    This exercises the normal flow where:
    - search -> replace commits are created
    - checkout back to search
    - original commit made
    - cherry-pick of replace onto original succeeds

    Oracle: the function returns the final file text equal to replace_text.
    """
    _patch_fakes(monkeypatch, raise_on_cherry=False)

    search_text = "alpha\n"
    replace_text = "beta\n"
    original_text = "gamma\n"

    result = sr.git_cherry_pick_sr_onto_so((search_text, replace_text, original_text))

    # On successful cherry-pick we expect the working file to contain the
    # replacement content (as our fake cherry_pick applies replace content).
    assert result == replace_text


def test_git_cherry_pick_conflict_round_077(monkeypatch):
    """Simulate a cherry-pick conflict where git raises an exception.

    This exercises the except branch that returns early when a GitError or
    ODBError occurs. Oracle: function returns None.
    """
    _patch_fakes(monkeypatch, raise_on_cherry=True)

    search_text = "one\n"
    replace_text = "two\n"
    original_text = "three\n"

    result = sr.git_cherry_pick_sr_onto_so((search_text, replace_text, original_text))

    # The function is expected to return None when a cherry-pick conflict is
    # encountered and caught.
    assert result is None
