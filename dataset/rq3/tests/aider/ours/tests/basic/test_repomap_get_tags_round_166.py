import importlib
import types

import pytest

# Import the module under test. If the project layout is different, pytest will report the import error.
repomap = importlib.import_module("aider.repomap")

# Define a custom error type for deterministic exception simulation and patch the module symbol
class CustomDBError(Exception):
    pass

# Patch the module-level SQLITE_ERRORS to match the except clauses in get_tags
repomap.SQLITE_ERRORS = (CustomDBError,)


def make_repo():
    """Create a RepoMap instance without calling __init__ and with instrumentation hooks."""
    RepoMap = repomap.RepoMap
    repo = object.__new__(RepoMap)
    # record errors signaled to tags_cache_error
    repo._recorded_errors = []

    def tags_cache_error(e):
        repo._recorded_errors.append(e)

    repo.tags_cache_error = tags_cache_error

    # default behaviours can be overridden by tests
    repo.save_tags_cache = lambda: None
    repo.get_tags_raw = lambda fname, rel: iter(())
    return repo


def test_get_tags_mtime_none_round_166():
    """When get_mtime returns None the method returns an empty list (lines ~236-237)."""
    repo = make_repo()
    repo.get_mtime = lambda fname: None
    # TAGS_CACHE should not be used in this code path, but provide a simple sentinel
    repo.TAGS_CACHE = {}

    result = repomap.RepoMap.get_tags(repo, "somefile", "rel")
    assert result == [], "Expected empty list when mtime is None"
    assert repo._recorded_errors == [], "No cache errors should be recorded"


def test_get_tags_cache_get_exception_then_return_cached_round_166():
    """Simulate TAGS_CACHE.get raising once (caught by except SQLITE_ERRORS) then returning a valid cache entry.
    This exercises the first try/except around TAGS_CACHE.get and the path returning cached data when mtime matches.
    """
    repo = make_repo()
    file_mtime = 123
    repo.get_mtime = lambda fname: file_mtime

    class FakeCache:
        def __init__(self):
            self._calls = 0
            self._store = {"/path/to/file": {"mtime": file_mtime, "data": ["a"]}}

        def get(self, key):
            self._calls += 1
            # first call raises, second call returns the stored value
            if self._calls == 1:
                raise CustomDBError("simulated get failure")
            return self._store.get(key)

        def __getitem__(self, key):
            return self._store[key]

        def __setitem__(self, key, value):
            self._store[key] = value

    fake = FakeCache()
    repo.TAGS_CACHE = fake

    result = repomap.RepoMap.get_tags(repo, "/path/to/file", "rel")
    assert result == ["a"], "Should return cached data after an initial get() failure and retry"
    # tags_cache_error should have been called once due to the first simulated get() raising
    assert len(repo._recorded_errors) == 1
    assert isinstance(repo._recorded_errors[0], CustomDBError)


def test_get_tags_cache_index_raises_then_succeeds_round_166():
    """Simulate __getitem__ raising on first access (caught by except SQLITE_ERRORS) then succeeding on the retry.
    This covers the branch where the cache entry exists and mtime matches but indexing raises.
    """
    repo = make_repo()
    file_mtime = 456
    repo.get_mtime = lambda fname: file_mtime

    class FakeCacheIndexFailThenSucceed:
        def __init__(self):
            self._getitem_calls = 0
            self._store = {"/file": {"mtime": file_mtime, "data": ["b"]}}

        def get(self, key):
            return self._store.get(key)

        def __getitem__(self, key):
            self._getitem_calls += 1
            if self._getitem_calls == 1:
                raise CustomDBError("simulated indexing failure")
            return self._store[key]

        def __setitem__(self, key, value):
            self._store[key] = value

    fake = FakeCacheIndexFailThenSucceed()
    repo.TAGS_CACHE = fake

    result = repomap.RepoMap.get_tags(repo, "/file", "rel")
    assert result == ["b"], "Should return cached data after __getitem__ raises then succeeds"
    assert len(repo._recorded_errors) == 1
    assert isinstance(repo._recorded_errors[0], CustomDBError)


def test_get_tags_cache_save_raises_round_166():
    """Simulate save_tags_cache raising SQLITE_ERRORS when updating the cache. Verify tags_cache_error is called and
    that the cache receives a setitem call with the expected shape. This covers the exception block around save_tags_cache
    (lines ~257-262).
    """
    repo = make_repo()
    file_mtime = 789
    repo.get_mtime = lambda fname: file_mtime
    # get_tags_raw yields two tags -> miss path
    repo.get_tags_raw = lambda fname, rel: iter(["c", "d"])

    class FakeCacheRecorder:
        def __init__(self):
            self.set_calls = []
            self._store = {}

        def get(self, key):
            # simulate a cache miss
            return None

        def __setitem__(self, key, value):
            self.set_calls.append((key, value))
            # persist into inner store to allow later retrieval if needed
            self._store[key] = value

        def __getitem__(self, key):
            return self._store[key]

    fake = FakeCacheRecorder()
    repo.TAGS_CACHE = fake

    # Make save_tags_cache raise on first call to simulate SQLITE_ERRORS during saving
    def save_then_raise():
        raise CustomDBError("simulated save failure")

    repo.save_tags_cache = save_then_raise

    result = repomap.RepoMap.get_tags(repo, "/some/file", "rel")
    assert result == ["c", "d"], "On miss, returned data should be the list produced by get_tags_raw"

    # tags_cache_error should have been called due to save_tags_cache raising
    assert len(repo._recorded_errors) == 1
    assert isinstance(repo._recorded_errors[0], CustomDBError)

    # Ensure the cache was attempted to be set at least once with the expected structure
    assert fake.set_calls, "Expected at least one setitem call to TAGS_CACHE"
    key, payload = fake.set_calls[0]
    assert isinstance(key, str)
    assert isinstance(payload, dict)
    assert payload.get("mtime") == file_mtime
    assert payload.get("data") == ["c", "d"]
