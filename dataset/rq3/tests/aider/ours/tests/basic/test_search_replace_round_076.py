import hashlib
from contextlib import contextmanager
from types import SimpleNamespace
from pathlib import Path
import pytest

from aider.coders import search_replace

# Helper to compute deterministic commit hash from file contents
def _content_hash(path: Path) -> str:
    data = path.read_text().encode()
    return hashlib.sha1(data).hexdigest()

def test_cherry_pick_success_round_076(tmp_path, monkeypatch):
    """
    Simulate a repo where cherry-pick applies cleanly. Expect the function
    to return the replace_text (R) after applying R onto O.
    """
    # Prepare texts: (search_text, replace_text, original_text)
    original = "original content\n"
    search = "search content\n"
    replace = "replace content\n"
    texts = (search, replace, original)

    # Patch GitTemporaryDirectory to yield our tmp_path directory
    @contextmanager
    def fake_git_tmpdir():
        yield tmp_path

    monkeypatch.setattr(search_replace, "GitTemporaryDirectory", fake_git_tmpdir)

    # Prepare a fake git.exc namespace with exceptions the code expects
    class FakeGitError(Exception):
        pass

    class FakeODBError(Exception):
        pass

    monkeypatch.setattr(search_replace.git, "exc", SimpleNamespace(GitError=FakeGitError, ODBError=FakeODBError))

    # FakeRepo simulates minimal git behavior used by the function
    class FakeRepo:
        def __init__(self, dname):
            # store working dir as Path
            self.root = Path(dname)
            self.git = SimpleNamespace()
            # mapping from commit hash -> file content string
            self._commits = {}

            # define git methods
            def add(path_str):
                # no-op for this fake
                return

            def commit(*args, **kwargs):
                # determine current file content and create a commit
                fpath = self.root / "file.txt"
                content = fpath.read_text()
                h = hashlib.sha1(content.encode()).hexdigest()
                # save mapping and set head
                self._commits[h] = content
                # attach a simple head.commit object
                self.head = SimpleNamespace(commit=SimpleNamespace(hexsha=h))

            def checkout(hashish):
                # write the file content corresponding to this commit
                content = self._commits.get(hashish)
                if content is None:
                    raise FakeGitError("unknown commit")
                fpath = self.root / "file.txt"
                fpath.write_text(content)
                # update head to point at checked out commit
                self.head = SimpleNamespace(commit=SimpleNamespace(hexsha=hashish))

            def cherry_pick(hashish, flag=None):
                # apply the content recorded for replace commit on top of current
                content = self._commits.get(hashish)
                if content is None:
                    raise FakeGitError("unknown commit")
                fpath = self.root / "file.txt"
                # simple deterministic behavior: replace file content with commit's content
                fpath.write_text(content)
                # create a new commit representing the cherry-pick result
                new_hash = hashlib.sha1((content + "+cherry").encode()).hexdigest()
                self._commits[new_hash] = content
                self.head = SimpleNamespace(commit=SimpleNamespace(hexsha=new_hash))

            self.git.add = add
            self.git.commit = commit
            self.git.checkout = checkout
            self.git.cherry_pick = cherry_pick

    # Patch Repo used in module to our FakeRepo
    monkeypatch.setattr(search_replace.git, "Repo", FakeRepo)

    # Call the function under test
    result = search_replace.git_cherry_pick_osr_onto_o(texts)

    # After a successful cherry-pick, function should return the replace_text
    assert result == replace

    # Ensure the file in tmp_path was updated to replace content as well
    file_text = (tmp_path / "file.txt").read_text()
    assert file_text == replace


def test_cherry_pick_conflict_round_076(tmp_path, monkeypatch):
    """
    Simulate a repo where cherry-pick raises a GitError (merge conflict)
    and the function returns early (None).
    """
    original = "original content\n"
    search = "search content\n"
    replace = "replace content\n"
    texts = (search, replace, original)

    @contextmanager
    def fake_git_tmpdir():
        yield tmp_path

    monkeypatch.setattr(search_replace, "GitTemporaryDirectory", fake_git_tmpdir)

    class FakeGitError(Exception):
        pass

    class FakeODBError(Exception):
        pass

    monkeypatch.setattr(search_replace.git, "exc", SimpleNamespace(GitError=FakeGitError, ODBError=FakeODBError))

    class FakeRepoConflict:
        def __init__(self, dname):
            self.root = Path(dname)
            self.git = SimpleNamespace()
            self._commits = {}

            def add(path_str):
                return

            def commit(*args, **kwargs):
                fpath = self.root / "file.txt"
                content = fpath.read_text()
                h = hashlib.sha1(content.encode()).hexdigest()
                self._commits[h] = content
                self.head = SimpleNamespace(commit=SimpleNamespace(hexsha=h))

            def checkout(hashish):
                content = self._commits.get(hashish)
                if content is None:
                    raise FakeGitError("unknown commit")
                fpath = self.root / "file.txt"
                fpath.write_text(content)
                self.head = SimpleNamespace(commit=SimpleNamespace(hexsha=hashish))

            def cherry_pick(hashish, flag=None):
                # Simulate a merge conflict by raising the GitError expected by the code
                raise FakeGitError("merge conflict simulated")

            self.git.add = add
            self.git.commit = commit
            self.git.checkout = checkout
            self.git.cherry_pick = cherry_pick

    monkeypatch.setattr(search_replace.git, "Repo", FakeRepoConflict)

    result = search_replace.git_cherry_pick_osr_onto_o(texts)

    # On merge conflict, function returns None
    assert result is None
