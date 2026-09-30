# file: aider/repomap.py:233-264
# asked: {"lines": [237, 242, 243, 244, 249, 250, 251, 260, 261, 262], "branches": [[236, 237]]}
# gained: {"lines": [237, 242, 243, 244, 249, 250, 251, 260, 261, 262], "branches": [[236, 237]]}

import pytest

import aider.repomap as repomap
from aider.repomap import RepoMap


class _RaiseThenReturnCache:
    """TAGS_CACHE-like object whose get raises the provided exception class once, then returns None.
    Also supports __setitem__ for storing values."""
    def __init__(self, exc_cls):
        self._count = 0
        self._store = {}
        self._exc_cls = exc_cls

    def get(self, key):
        if self._count == 0:
            self._count += 1
            raise self._exc_cls("simulated get error")
        return None

    def __setitem__(self, key, value):
        self._store[key] = value

    def __getitem__(self, key):
        return self._store[key]


def test_get_tags_mtime_none(monkeypatch):
    rm = RepoMap()
    monkeypatch.setattr(rm, "get_mtime", lambda fname: None)
    assert rm.get_tags("somefile.py", "somefile.py") == []


def test_get_tags_cache_get_raises_then_none_and_save(monkeypatch):
    # Arrange
    rm = RepoMap()
    file_mtime = 12345
    monkeypatch.setattr(rm, "get_mtime", lambda fname: file_mtime)

    # Use a concrete exception class from SQLITE_ERRORS
    sqlite_exc_cls = repomap.sqlite3.OperationalError

    cache_obj = _RaiseThenReturnCache(sqlite_exc_cls)
    # Patch the instance attribute TAGS_CACHE to our object (RepoMap.__init__ may set instance attr)
    monkeypatch.setattr(rm, "TAGS_CACHE", cache_obj, raising=False)

    called = {"tags_cache_error": 0, "saved": False}

    def fake_tags_cache_error(e):
        called["tags_cache_error"] += 1
        assert isinstance(e, sqlite_exc_cls)

    def fake_get_tags_raw(fname, rel_fname):
        return ("tag-" + fname,)

    def fake_save_tags_cache():
        called["saved"] = True

    monkeypatch.setattr(rm, "tags_cache_error", fake_tags_cache_error)
    monkeypatch.setattr(rm, "get_tags_raw", fake_get_tags_raw)
    monkeypatch.setattr(rm, "save_tags_cache", fake_save_tags_cache)

    # Act
    result = rm.get_tags("fileA.py", "fileA.py")

    # Assert
    assert called["tags_cache_error"] == 1
    assert called["saved"] is True
    assert result == ["tag-fileA.py"]
    cached = cache_obj._store.get("fileA.py")
    assert cached is not None
    assert cached["mtime"] == file_mtime
    assert cached["data"] == ["tag-fileA.py"]


def test_get_tags_cached_item_getitem_raises_then_succeeds(monkeypatch):
    rm = RepoMap()
    file_mtime = 2222
    monkeypatch.setattr(rm, "get_mtime", lambda fname: file_mtime)

    sqlite_exc_cls = repomap.sqlite3.OperationalError

    class CacheObj:
        def __init__(self):
            self._getitem_count = 0

        def get(self, key):
            return {"mtime": file_mtime}

        def __getitem__(self, key):
            if self._getitem_count == 0:
                self._getitem_count += 1
                raise sqlite_exc_cls("simulated __getitem__ fail")
            return {"data": ["cached-tag"]}

    cache_obj = CacheObj()
    # set on instance to ensure it's used
    monkeypatch.setattr(rm, "TAGS_CACHE", cache_obj, raising=False)

    called = {"tags_cache_error": 0}

    def fake_tags_cache_error(e):
        called["tags_cache_error"] += 1
        assert isinstance(e, sqlite_exc_cls)

    monkeypatch.setattr(rm, "tags_cache_error", fake_tags_cache_error)

    result = rm.get_tags("fileB.py", "fileB.py")

    assert result == ["cached-tag"]
    assert called["tags_cache_error"] == 1


def test_save_tags_cache_raises_sets_cache_in_except(monkeypatch):
    rm = RepoMap()
    file_mtime = 3333
    monkeypatch.setattr(rm, "get_mtime", lambda fname: file_mtime)

    cache_dict = {}
    # set on instance to ensure it's used
    monkeypatch.setattr(rm, "TAGS_CACHE", cache_dict, raising=False)

    sqlite_exc_cls = repomap.sqlite3.OperationalError

    called = {"tags_cache_error": 0}

    def fake_tags_cache_error(e):
        called["tags_cache_error"] += 1
        assert isinstance(e, sqlite_exc_cls)

    def fake_get_tags_raw(fname, rel_fname):
        return ("t1", "t2")

    def fake_save_tags_cache():
        raise sqlite_exc_cls("simulated save error")

    monkeypatch.setattr(rm, "tags_cache_error", fake_tags_cache_error)
    monkeypatch.setattr(rm, "get_tags_raw", fake_get_tags_raw)
    monkeypatch.setattr(rm, "save_tags_cache", fake_save_tags_cache)

    result = rm.get_tags("fileC.py", "fileC.py")

    assert result == ["t1", "t2"]
    assert called["tags_cache_error"] == 1
    assert "fileC.py" in cache_dict
    assert cache_dict["fileC.py"]["mtime"] == file_mtime
    assert cache_dict["fileC.py"]["data"] == ["t1", "t2"]
