# file: aider/models.py:191-209
# asked: {"lines": [201, 202, 203, 204, 205, 207, 208, 209], "branches": [[197, 0]]}
# gained: {"lines": [201, 202, 203, 204, 205, 207, 208, 209], "branches": [[197, 0]]}

import sys
import types
import pytest

from aider.models import ModelInfoManager


def make_requests_module(get_callable):
    mod = types.ModuleType("requests")
    mod.get = get_callable
    return mod


def test_update_cache_success_write_oserror(monkeypatch):
    """
    Simulate a successful HTTP 200 response whose JSON is set to manager.content,
    but writing to the cache file raises OSError. This should exercise the inner
    OSError except block (lines 201-202) while still setting manager.content.
    """
    manager = ModelInfoManager()

    class Response:
        status_code = 200

        def json(self):
            return {"model": "x", "price": 1.23}

    def fake_get(url, timeout, verify):
        # Verify that verify arg from manager is passed through
        assert timeout == 5
        return Response()

    # Install fake requests module
    monkeypatch.setitem(sys.modules, "requests", make_requests_module(fake_get))

    # Make cache_file.write_text raise OSError to hit the inner except
    class BadCacheFile:
        def write_text(self, text):
            raise OSError("cannot write cache")

    manager.cache_file = BadCacheFile()
    manager.verify_ssl = False  # Ensure value is passed but doesn't matter

    # Call method; should not raise, and content should be set from response.json()
    manager._update_cache()
    assert manager.content == {"model": "x", "price": 1.23}


def test_update_cache_non_200_branch(monkeypatch):
    """
    Simulate a non-200 response (e.g., 404). This should exercise the branch
    where response.status_code != 200 and exit without setting content or writing cache.
    """
    manager = ModelInfoManager()

    class Response:
        status_code = 404

    def fake_get(url, timeout, verify):
        assert timeout == 5
        return Response()

    monkeypatch.setitem(sys.modules, "requests", make_requests_module(fake_get))

    # Use a cache_file that would raise if written to, to detect any unexpected writes.
    class ShouldNotBeCalledCacheFile:
        def write_text(self, text):
            raise AssertionError("write_text should not be called for non-200 responses")

    manager.cache_file = ShouldNotBeCalledCacheFile()

    # Ensure content is None before call
    manager.content = None
    manager._update_cache()
    # For non-200 response, content should remain unchanged (None)
    assert manager.content is None


def test_update_cache_requests_exception_and_cache_write_oserror(monkeypatch, capsys):
    """
    Simulate requests.get raising an exception so the outer except(Exception) block runs.
    Then ensure that attempting to write an empty dict to cache_file raises OSError and
    is swallowed by the inner except (lines 207-209). Also capture printed exception text.
    """
    manager = ModelInfoManager()

    def fake_get_raising(url, timeout, verify):
        raise RuntimeError("network down")

    monkeypatch.setitem(sys.modules, "requests", make_requests_module(fake_get_raising))

    class BadCacheFile:
        def write_text(self, text):
            # The outer except tries to write "{}" to cache_file; simulate OSError here
            raise OSError("disk full")

    manager.cache_file = BadCacheFile()

    # Should not raise despite underlying errors
    manager._update_cache()

    captured = capsys.readouterr()
    # Outer exception should have been printed
    assert "network down" in captured.out
