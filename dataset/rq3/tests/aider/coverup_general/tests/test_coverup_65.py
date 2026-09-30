# file: aider/repo.py:433-488
# asked: {"lines": [435, 441, 442, 443, 444, 445, 463, 464, 467, 470, 471, 472, 473, 474, 483, 484], "branches": [[434, 435]]}
# gained: {"lines": [435, 441, 442, 443, 444, 445, 463, 464, 467, 470, 471, 472, 473, 474, 483, 484], "branches": [[434, 435]]}

import pytest
import git

from aider import repo as repo_module
from aider.repo import GitRepo


class DummyIO:
    def __init__(self):
        self.errors = []
        self.outputs = []
        self.warnings = []

    def tool_error(self, msg):
        self.errors.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)

    def tool_warning(self, msg):
        self.warnings.append(msg)


class FakeBlob:
    def __init__(self, type_, path):
        self.type = type_
        self.path = path


class IteratorWithIndexError:
    """Iterator that yields one blob, then raises IndexError once, then yields another blob, then stops."""

    def __init__(self, blobs):
        # blobs is list of FakeBlob objects to yield normally; we'll inject an IndexError between first and second
        self.blobs = blobs
        self.state = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.state == 0:
            self.state += 1
            return self.blobs[0]
        if self.state == 1:
            self.state += 1
            raise IndexError("simulated index error")
        if self.state == 2:
            self.state += 1
            return self.blobs[1]
        raise StopIteration


class SimpleIterator:
    """Iterator that raises a specified exception when next() is called, or yields blobs if provided."""
    def __init__(self, to_raise=None, blobs=None):
        self.to_raise = to_raise
        self.blobs = blobs or []
        self.idx = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.to_raise is not None:
            raise self.to_raise
        if self.idx < len(self.blobs):
            b = self.blobs[self.idx]
            self.idx += 1
            return b
        raise StopIteration


class FakeTree:
    def __init__(self, iterator):
        self._iterator = iterator

    def traverse(self):
        return self._iterator


class FakeCommit:
    def __init__(self, tree):
        self.tree = tree


class FakeHeadRaises:
    def __init__(self, exc):
        self._exc = exc

    @property
    def commit(self):
        raise self._exc


class FakeHeadValueError:
    @property
    def commit(self):
        raise ValueError("no commit")


class FakeIndex:
    def __init__(self, keys_iter):
        # keys_iter should be an iterable that will be returned by entries.keys()
        self.entries = DummyEntries(keys_iter)


class DummyEntries:
    def __init__(self, keys_iter):
        self._keys_iter = keys_iter

    def keys(self):
        # Return an iterable of (path, something)
        return self._keys_iter


def make_repo_with_head_and_index(head_obj, index_obj):
    fake_repo = type("Repo", (), {})()
    fake_repo.head = head_obj
    fake_repo.index = index_obj
    return fake_repo


def make_instance_without_init():
    # Create GitRepo instance without running __init__
    inst = object.__new__(GitRepo)
    # Set necessary attributes used by get_tracked_files
    inst.io = DummyIO()
    inst.normalized_path = {}
    inst.tree_files = {}
    inst.attribute_author = True
    inst.attribute_committer = True
    inst.attribute_commit_message_author = False
    inst.attribute_commit_message_committer = False
    inst.attribute_co_authored_by = False
    inst.commit_prompt = None
    inst.subtree_only = False
    inst.git_commit_verify = True
    inst.ignore_file_cache = {}
    # Helper methods expected
    inst.normalize_path = lambda s: s
    inst.ignored_file = lambda s: False
    inst.git_repo_error = None
    return inst


def test_get_tracked_files_repo_none():
    inst = make_instance_without_init()
    inst.repo = None
    res = inst.get_tracked_files()
    assert res == [], "Expected empty list when repo is falsy/None"


def test_get_tracked_files_head_commit_git_error_sets_git_repo_error_and_outputs():
    inst = make_instance_without_init()
    # head.commit will raise a git.GitError which is part of ANY_GIT_ERROR
    inst.repo = make_repo_with_head_and_index(FakeHeadRaises(git.exc.GitError("boom")), index_obj=FakeIndex([]))
    res = inst.get_tracked_files()
    # Should have recorded the error, output a corruption hint, and return []
    assert res == []
    assert isinstance(inst.git_repo_error, git.exc.GitError)
    assert any("Unable to list files in git repo" in e for e in inst.io.errors)
    assert any("Is your git repo corrupted?" in o for o in inst.io.outputs)


def test_get_tracked_files_commit_none_reads_staged_files():
    inst = make_instance_without_init()
    # head.commit raises ValueError -> commit None
    head = FakeHeadValueError()
    # index.entries.keys yields pairs (path, something)
    index_keys = [("a.txt", 0), ("b.txt", 0)]
    index = FakeIndex(index_keys)
    inst.repo = make_repo_with_head_and_index(head, index)
    res = inst.get_tracked_files()
    assert set(res) == {"a.txt", "b.txt"}


def test_get_tracked_files_traverse_handles_index_error_and_collects_blobs():
    inst = make_instance_without_init()
    # Create blobs and an iterator that yields blob1, IndexError, blob2
    blob1 = FakeBlob("blob", "first.txt")
    blob2 = FakeBlob("blob", "second.txt")
    iterator = IteratorWithIndexError([blob1, blob2])
    tree = FakeTree(iterator)
    commit = FakeCommit(tree)
    # head.commit returns this commit
    head = type("Head", (), {"commit": commit})()
    # index with no staged files
    index = FakeIndex([])
    inst.repo = make_repo_with_head_and_index(head, index)
    res = inst.get_tracked_files()
    # Both files should be present
    assert set(res) == {"first.txt", "second.txt"}
    # A warning for the index error should have been recorded
    assert any("GitRepo: Index error encountered while reading git tree object" in w for w in inst.io.warnings)


def test_get_tracked_files_traverse_any_git_error_reports_and_returns_empty():
    inst = make_instance_without_init()
    # Make traverse raise a git error immediately
    iterator = SimpleIterator(to_raise=git.exc.GitError("traverse fail"))
    tree = FakeTree(iterator)
    commit = FakeCommit(tree)
    head = type("Head", (), {"commit": commit})()
    index = FakeIndex([])
    inst.repo = make_repo_with_head_and_index(head, index)
    res = inst.get_tracked_files()
    assert res == []
    assert isinstance(inst.git_repo_error, git.exc.GitError)
    assert any("Unable to list files in git repo" in e for e in inst.io.errors)
    assert any("Is your git repo corrupted?" in o for o in inst.io.outputs)


def test_get_tracked_files_index_entries_giterror_reports_but_returns_files_from_tree_if_any():
    inst = make_instance_without_init()
    # Create a commit that yields one blob
    blob = FakeBlob("blob", "tree_only.txt")
    iterator = SimpleIterator(blobs=[blob])
    tree = FakeTree(iterator)
    commit = FakeCommit(tree)
    head = type("Head", (), {"commit": commit})()
    # Make index.entries.keys raise a git error when iterated
    class BadEntries:
        def keys(self):
            raise git.exc.GitError("index read fail")

    index = type("Idx", (), {"entries": BadEntries()})()
    inst.repo = make_repo_with_head_and_index(head, index)
    res = inst.get_tracked_files()
    # Should have the tree file despite index read error
    assert set(res) == {"tree_only.txt"}
    # And error was logged for staged files read failure
    assert any("Unable to read staged files" in e for e in inst.io.errors)
