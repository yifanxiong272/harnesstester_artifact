import importlib
from types import SimpleNamespace
import pytest

# Import the module under test
import aider.watch as watch

# A lightweight, deterministic fake Path-like object factory.
# We'll monkeypatch watch.Path to return these objects for requested path strings.
class FakeRelPath:
    def __init__(self, val):
        self._val = val

    def as_posix(self):
        return self._val

    def __repr__(self):
        return f"<Rel:{self._val}>"


class FakePath:
    # registry maps the exact path string passed to Path(...) to a config dict
    registry = {}

    def __init__(self, key):
        cfg = self.registry.get(key, {})
        self._key = key
        # base is used for is_relative_to comparisons
        self.base = cfg.get("base", (key.split("/")[0] if key else ""))
        # is_file/is_dir flags
        self._is_file = cfg.get("is_file", ("." in (key.split("/")[-1]) if key else False) and not cfg.get("is_dir", False))
        self._is_dir = cfg.get("is_dir", False)
        # numeric size for stat().st_size
        self._size = cfg.get("size", 0)
        # relative path string returned by relative_to
        self._rel = cfg.get("rel", "/".join(key.split("/")[1:]) if "/" in key else key)

    def absolute(self):
        # behave like pathlib.Path.absolute(); return self for simplicity
        return self

    def is_relative_to(self, other):
        # other may be a FakePath or a real object; compare base markers
        other_base = getattr(other, "base", getattr(other, "_key", None))
        return self.base == other_base

    def relative_to(self, root):
        # return a small object that implements as_posix()
        return FakeRelPath(self._rel)

    def as_posix(self):
        return self._key

    def is_dir(self):
        return bool(self._is_dir)

    def is_file(self):
        return bool(self._is_file)

    def stat(self):
        class S:
            pass

        s = S()
        s.st_size = self._size
        return s

    def __repr__(self):
        return f"<FakePath {self._key} base={self.base} file={self._is_file} dir={self._is_dir} size={self._size}>"


# Helper to install the fake Path factory into the module under test
def patch_watch_path(registry):
    FakePath.registry = registry.copy()
    # Patch the Path symbol in the module under test
    watch.Path = lambda p: FakePath(p)


# TESTS

def test_filter_not_under_root_round_061():
    # Path not relative to root -> should return False
    registry = {
        # the path passed to filter_func
        "outside/file.txt": {"base": "outside", "is_file": True, "size": 10},
    }
    patch_watch_path(registry)

    # Create a simple watcher-like object with minimal attributes used by filter_func
    fake_root = FakePath("root")
    watcher = SimpleNamespace(root=fake_root, gitignore_spec=None, verbose=False)

    # get_ai_comments should not be called in this branch, but provide a deterministic stub
    watcher.get_ai_comments = lambda p: ([], None, None)

    result = watch.FileWatcher.filter_func(watcher, "modified", "outside/file.txt")
    assert result is False


def test_filter_verbose_and_ai_comments_round_061(capsys):
    # Path is under root, verbose True -> prints and returns True when AI comments detected
    registry = {
        "root/subdir/code.py": {"base": "root", "is_file": True, "size": 100},
    }
    patch_watch_path(registry)

    fake_root = FakePath("root")
    watcher = SimpleNamespace(root=fake_root, gitignore_spec=None, verbose=True)

    # Provide get_ai_comments that returns a non-empty comments list
    watcher.get_ai_comments = lambda p: (["generated-by-ai"], None, None)

    result = watch.FileWatcher.filter_func(watcher, "modified", "root/subdir/code.py")

    captured = capsys.readouterr()
    # The function should have printed at least the words 'Changed' and 'Checking' in verbose mode
    assert "Changed" in captured.out
    assert "Checking" in captured.out
    assert result is True


def test_filter_gitignore_match_round_061():
    # Path under root but gitignore_spec.match_file returns True -> should return False
    registry = {
        "root/ignored.txt": {"base": "root", "is_file": True, "size": 10, "rel": "ignored.txt"},
    }
    patch_watch_path(registry)

    fake_root = FakePath("root")

    class DummySpec:
        def match_file(self, p):
            # Expect the rel_path.as_posix() + trailing slash if dir; ensure deterministic
            assert isinstance(p, str)
            return True

    watcher = SimpleNamespace(root=fake_root, gitignore_spec=DummySpec(), verbose=False)
    watcher.get_ai_comments = lambda p: ([], None, None)

    result = watch.FileWatcher.filter_func(watcher, "modified", "root/ignored.txt")
    assert result is False


def test_filter_large_file_round_061():
    # Path under root, file size > 1MB -> should return False
    large_size = 2 * 1024 * 1024
    registry = {
        "root/big.bin": {"base": "root", "is_file": True, "size": large_size, "rel": "big.bin"},
    }
    patch_watch_path(registry)

    fake_root = FakePath("root")
    watcher = SimpleNamespace(root=fake_root, gitignore_spec=None, verbose=False)
    watcher.get_ai_comments = lambda p: ([], None, None)

    result = watch.FileWatcher.filter_func(watcher, "modified", "root/big.bin")
    assert result is False


def test_filter_get_ai_exception_round_061():
    # get_ai_comments raises an exception -> filter_func should swallow and return None
    registry = {
        "root/problem.py": {"base": "root", "is_file": True, "size": 10, "rel": "problem.py"},
    }
    patch_watch_path(registry)

    fake_root = FakePath("root")
    watcher = SimpleNamespace(root=fake_root, gitignore_spec=None, verbose=False)

    def raising_get_ai(path):
        raise RuntimeError("parse error")

    watcher.get_ai_comments = raising_get_ai

    result = watch.FileWatcher.filter_func(watcher, "modified", "root/problem.py")
    # The except branch returns with no value -> None
    assert result is None
