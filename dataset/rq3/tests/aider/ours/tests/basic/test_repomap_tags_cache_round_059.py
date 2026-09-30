import pytest
from pathlib import Path

import aider.repomap as repomap


class DummyIO:
    def __init__(self):
        self.warnings = []
        self.outputs = []

    def tool_warning(self, msg):
        self.warnings.append(str(msg))

    def tool_output(self, msg):
        self.outputs.append(str(msg))


class FakeCache:
    """A minimal dict-like cache to mimic diskcache.Cache behavior used in tags_cache_error."""

    def __init__(self, path):
        # Record the path for assertions
        self._path = Path(path)
        self._store = {}

    def __setitem__(self, k, v):
        self._store[k] = v

    def __getitem__(self, k):
        return self._store[k]

    def __delitem__(self, k):
        del self._store[k]


def make_repomap_instance(root, io=None, verbose=False):
    # Bypass __init__ to avoid side effects and control attributes deterministically
    rm = repomap.RepoMap.__new__(repomap.RepoMap)
    rm.io = io or DummyIO()
    rm.verbose = verbose
    rm.root = str(root)
    # Do not call load_tags_cache; set TAGS_CACHE explicitly when needed
    return rm


def test_tags_cache_error_when_dict_and_verbose_round_059(monkeypatch, tmp_path):
    io = DummyIO()
    rm = make_repomap_instance(root=tmp_path, io=io, verbose=True)

    # If TAGS_CACHE is already a dict, function should early-return after warning
    rm.TAGS_CACHE = {"existing": "value"}

    # Call with original_error to trigger the first warning branch
    exc = ValueError("boom")
    rm.tags_cache_error(original_error=exc)

    # Expect initial warning about tags cache error and TAGS_CACHE unchanged
    assert any("Tags cache error" in w for w in io.warnings), io.warnings
    assert rm.TAGS_CACHE == {"existing": "value"}


def test_tags_cache_error_recreates_cache_when_exists_false_round_059(monkeypatch, tmp_path):
    io = DummyIO()
    rm = make_repomap_instance(root=tmp_path, io=io, verbose=False)

    # Ensure no preexisting TAGS_CACHE
    rm.TAGS_CACHE = None

    # Ensure cache directory does NOT exist so shutil.rmtree branch is skipped
    cache_dir = Path(rm.root) / rm.TAGS_CACHE_DIR
    if cache_dir.exists():
        # remove if any leftover (deterministic test environment ensures none)
        for _ in cache_dir.rglob("*"):
            pass

    # Patch Cache to our FakeCache so creation and basic operations succeed
    monkeypatch.setattr(repomap, "Cache", FakeCache)

    # Patch shutil.rmtree to ensure it's not accidentally invoked (shouldn't be)
    called = {"rmtree": False}

    def fake_rmtree(p):
        called["rmtree"] = True

    monkeypatch.setattr(repomap.shutil, "rmtree", fake_rmtree)

    # Call without original_error, verbose False -> no initial warning
    rm.tags_cache_error(original_error=None)

    # Since directory did not exist, rmtree should not have been called
    assert called["rmtree"] is False

    # TAGS_CACHE should be our FakeCache instance and support set/get/del
    assert isinstance(rm.TAGS_CACHE, FakeCache)
    # Verify FakeCache works by evaluating its store through the instance
    rm.TAGS_CACHE["test"] = "testval"
    assert rm.TAGS_CACHE["test"] == "testval"
    del rm.TAGS_CACHE["test"]
    assert "test" not in rm.TAGS_CACHE._store

    # No warnings should have been emitted in this path
    assert io.warnings == []


def test_tags_cache_error_fallback_on_sqlite_error_round_059(monkeypatch, tmp_path):
    io = DummyIO()
    rm = make_repomap_instance(root=tmp_path, io=io, verbose=True)

    # Start with no cache so code will attempt recreation
    rm.TAGS_CACHE = None

    # Ensure cache dir exists so shutil.rmtree branch is exercised
    cache_dir = Path(rm.root) / rm.TAGS_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Create a custom exception type to simulate SQLITE_ERRORS
    class FakeSQLiteError(Exception):
        pass

    # Patch the module-level SQLITE_ERRORS to include our fake exception
    monkeypatch.setattr(repomap, "SQLITE_ERRORS", (FakeSQLiteError,))

    # Patch Cache to raise the sqlite-like error when instantiated
    def raising_cache(path):
        raise FakeSQLiteError("disk failure")

    monkeypatch.setattr(repomap, "Cache", raising_cache)

    # Patch shutil.rmtree to a no-op that records the call (so we don't delete the tmp dir)
    called = {"rmtree": False}

    def fake_rmtree(p):
        called["rmtree"] = True

    monkeypatch.setattr(repomap.shutil, "rmtree", fake_rmtree)

    # Call to trigger the exception path and fallback
    rm.tags_cache_error(original_error=None)

    # rmtree should have been called because cache_dir existed
    assert called["rmtree"] is True

    # Expect two warnings: unable to use tags cache and cache recreation error (because verbose=True)
    assert any("Unable to use tags cache" in w for w in io.warnings), io.warnings
    assert any("Cache recreation error" in w for w in io.warnings), io.warnings

    # After failure, TAGS_CACHE should be a plain dict fallback
    assert isinstance(rm.TAGS_CACHE, dict)
