import pytest

import types

import aider.repo as repo_mod


class CustomError(Exception):
    pass


class FakeIO:
    def __init__(self):
        self.errors = []
        self.outputs = []
        self.warnings = []

    def tool_error(self, msg):
        self.errors.append(str(msg))

    def tool_output(self, msg):
        self.outputs.append(str(msg))

    def tool_warning(self, msg):
        self.warnings.append(str(msg))


def make_repo_instance():
    """Create an uninitialized GitRepo-like instance for testing by
    bypassing __init__ and setting only the attributes needed by
    get_tracked_files."""
    obj = object.__new__(repo_mod.GitRepo)
    obj.io = FakeIO()
    obj.tree_files = {}
    obj.git_repo_error = None
    obj.normalize_path = lambda p: p
    obj.ignored_file = lambda fname: False
    return obj


def test_get_tracked_files_no_repo_round_113():
    # Branch: if not self.repo -> immediate [] (line 435)
    repo = make_repo_instance()
    repo.repo = None

    # Ensure ANY_GIT_ERROR is set to a concrete exception class for the method
    repo_mod.ANY_GIT_ERROR = CustomError

    res = repo.get_tracked_files()
    assert res == []
    # No errors or outputs should have been recorded
    assert repo.io.errors == []
    assert repo.io.outputs == []


def test_get_tracked_files_head_commit_any_git_error_round_113():
    # Branch: accessing head.commit raises ANY_GIT_ERROR -> records error, outputs, returns [] (441-445)
    repo = make_repo_instance()

    class BadHead:
        @property
        def commit(self):
            raise CustomError("head access failed")

    fake_repo_obj = types.SimpleNamespace()
    fake_repo_obj.head = BadHead()
    # index is present but should not be reached because the method should return early
    fake_repo_obj.index = types.SimpleNamespace(entries={}.keys)

    repo.repo = fake_repo_obj

    # Patch module-level ANY_GIT_ERROR to match the raised exception
    repo_mod.ANY_GIT_ERROR = CustomError

    res = repo.get_tracked_files()

    assert res == []
    # git_repo_error should have been set to the exception instance
    assert isinstance(repo.git_repo_error, CustomError)
    # io should have recorded an error and an output message
    assert any("Unable to list files in git repo" in e for e in repo.io.errors)
    assert any("Is your git repo corrupted?" in o for o in repo.io.outputs)


def test_get_tracked_files_traverse_indexerror_and_staged_ioerror_round_113():
    # Branch: traversal yields a blob, then raises IndexError (should call tool_warning and continue),
    # and later staged files access raises ANY_GIT_ERROR -> tool_error called and final result still contains file from tree (463-467, 483-484)
    repo = make_repo_instance()

    class FakeBlob:
        def __init__(self, p):
            self.type = "blob"
            self.path = p

    class TraverseIterator:
        def __init__(self):
            self.calls = 0

        def __iter__(self):
            return self

        def __next__(self):
            # First call -> return a blob
            if self.calls == 0:
                self.calls += 1
                return FakeBlob("file1.txt")
            # Second call -> raise IndexError to hit the inner except branch
            if self.calls == 1:
                self.calls += 1
                raise IndexError("simulated index error")
            # Third call -> end iteration
            raise StopIteration

    class FakeTree:
        def traverse(self):
            return TraverseIterator()

    class FakeCommit:
        def __init__(self):
            self.tree = FakeTree()

    class BadIndexEntries:
        def keys(self):
            # Simulate ANY_GIT_ERROR when trying to read staged files
            raise CustomError("staged read failed")

    fake_repo_obj = types.SimpleNamespace()
    fake_repo_obj.head = types.SimpleNamespace(commit=FakeCommit())
    fake_repo_obj.index = types.SimpleNamespace(entries=BadIndexEntries())

    repo.repo = fake_repo_obj

    # Ensure module ANY_GIT_ERROR matches the raised CustomError
    repo_mod.ANY_GIT_ERROR = CustomError

    res = repo.get_tracked_files()

    # The traversal produced 'file1.txt' and staged files read failed; result should include the file from tree
    assert set(res) == {"file1.txt"}
    # tool_warning should have been invoked due to IndexError during traversal
    assert any("Index error encountered" in w for w in repo.io.warnings)
    # tool_error should have been invoked for the staged files read error
    assert any("Unable to read staged files" in e for e in repo.io.errors)


def test_get_tracked_files_traverse_any_git_error_round_113():
    # Branch: commit.tree.traverse() raises ANY_GIT_ERROR -> error recorded, output written, returns [] (470-474)
    repo = make_repo_instance()

    class FakeTree:
        def traverse(self):
            raise CustomError("traverse failure")

    class FakeCommit:
        def __init__(self):
            self.tree = FakeTree()

    fake_repo_obj = types.SimpleNamespace()
    fake_repo_obj.head = types.SimpleNamespace(commit=FakeCommit())
    fake_repo_obj.index = types.SimpleNamespace(entries={}.keys)

    repo.repo = fake_repo_obj

    repo_mod.ANY_GIT_ERROR = CustomError

    res = repo.get_tracked_files()

    assert res == []
    assert isinstance(repo.git_repo_error, CustomError)
    assert any("Unable to list files in git repo" in e for e in repo.io.errors)
    assert any("Is your git repo corrupted?" in o for o in repo.io.outputs)
