# file: gpt_researcher/llm_provider/image/modelslab_image_generator.py:84-121
# asked: {"lines": [86, 87, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 104, 105, 107, 108, 109, 110, 111, 112, 113, 115, 116, 117, 118, 119, 121], "branches": [[89, 90], [89, 121], [98, 99], [98, 100], [100, 89], [100, 101], [107, 108], [107, 121], [116, 117], [116, 118], [118, 107], [118, 119]]}
# gained: {"lines": [86, 87, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 104, 105, 107, 108, 109, 110, 111, 112, 113, 115, 116, 117, 118, 119, 121], "branches": [[89, 90], [89, 121], [98, 99], [98, 100], [100, 89], [100, 101], [107, 108], [116, 117], [116, 118], [118, 119]]}

import asyncio
import importlib
import sys
import types
import builtins

import pytest


MODULE_PATH = "gpt_researcher.llm_provider.image.modelslab_image_generator"


@pytest.fixture(autouse=True)
def reload_module_between_tests():
    # Ensure a fresh import for each test to avoid state leaking (like altered constants)
    if MODULE_PATH in sys.modules:
        del sys.modules[MODULE_PATH]
    yield
    if MODULE_PATH in sys.modules:
        del sys.modules[MODULE_PATH]


def _get_module():
    return importlib.import_module(MODULE_PATH)


async def _noop_sleep(_):
    return None


def _make_aiohttp_module(bodies):
    """
    Create a fake aiohttp module where each call to session.post() returns the next body
    (yielded from 'bodies' iterable) as the result of await resp.json().
    """
    mod = types.ModuleType("aiohttp")
    # iterator over provided bodies
    mod._bodies = iter(bodies)

    class FakeResponse:
        def __init__(self, body):
            self._body = body

        async def json(self):
            return self._body

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json, timeout):
            try:
                body = next(mod._bodies)
            except StopIteration:
                # default to pending if bodies exhausted
                body = {"status": "pending"}
            return FakeResponse(body)

    # simple ClientTimeout placeholder
    mod.ClientTimeout = lambda total=None: object()
    mod.ClientSession = lambda: FakeSession()
    return mod


@pytest.mark.asyncio
async def test_poll_for_result_aiohttp_success(monkeypatch):
    mod = _get_module()
    provider = mod.ModelsLabImageGeneratorProvider(api_key="testkey")

    # Prepare aiohttp to return a successful result immediately
    bodies = [{"status": "success", "output": ["http://example.com/img1.png"]}]
    fake_aio = _make_aiohttp_module(bodies)
    monkeypatch.setitem(sys.modules, "aiohttp", fake_aio)
    # Avoid real sleeping
    monkeypatch.setattr(asyncio, "sleep", _noop_sleep)

    result = await provider._poll_for_result("req-id-1")
    assert result == ["http://example.com/img1.png"]


@pytest.mark.asyncio
async def test_poll_for_result_aiohttp_error_raises(monkeypatch):
    mod = _get_module()
    provider = mod.ModelsLabImageGeneratorProvider(api_key="testkey")

    # Prepare aiohttp to return an error result
    bodies = [{"status": "error", "messege": "boom"}]
    fake_aio = _make_aiohttp_module(bodies)
    monkeypatch.setitem(sys.modules, "aiohttp", fake_aio)
    monkeypatch.setattr(asyncio, "sleep", _noop_sleep)

    with pytest.raises(RuntimeError) as exc:
        await provider._poll_for_result("req-id-err")
    assert "boom" in str(exc.value)


@pytest.mark.asyncio
async def test_poll_for_result_requests_success(monkeypatch):
    mod = _get_module()
    provider = mod.ModelsLabImageGeneratorProvider(api_key="testkey")

    # Ensure aiohttp import raises ImportError to exercise the requests fallback
    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "aiohttp" or name.startswith("aiohttp."):
            raise ImportError("No aiohttp for test")
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    # Make MAX_POLL_ATTEMPTS small to keep test quick
    monkeypatch.setattr(mod, "MAX_POLL_ATTEMPTS", 3)

    # Create a fake requests.Response-like object with a synchronous json() method
    class FakeResp:
        def __init__(self, body):
            self._body = body

        def json(self):
            return self._body

    # to_thread should return our FakeResp
    async def fake_to_thread(func, *args, **kwargs):
        # return a success body
        return FakeResp({"status": "success", "output": ["http://example.com/req-img.png"]})

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(asyncio, "sleep", _noop_sleep)

    result = await provider._poll_for_result("req-id-requests")
    assert result == ["http://example.com/req-img.png"]


@pytest.mark.asyncio
async def test_poll_for_result_requests_error_raises(monkeypatch):
    mod = _get_module()
    provider = mod.ModelsLabImageGeneratorProvider(api_key="testkey")

    # Ensure aiohttp import raises ImportError
    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "aiohttp" or name.startswith("aiohttp."):
            raise ImportError("No aiohttp for test")
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    monkeypatch.setattr(mod, "MAX_POLL_ATTEMPTS", 3)

    class FakeResp:
        def __init__(self, body):
            self._body = body

        def json(self):
            return self._body

    async def fake_to_thread(func, *args, **kwargs):
        return FakeResp({"status": "error", "messege": "requests-boom"})

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(asyncio, "sleep", _noop_sleep)

    with pytest.raises(RuntimeError) as exc:
        await provider._poll_for_result("req-id-err-requests")
    assert "requests-boom" in str(exc.value)


@pytest.mark.asyncio
async def test_poll_for_result_timeout_raises(monkeypatch):
    mod = _get_module()
    provider = mod.ModelsLabImageGeneratorProvider(api_key="testkey")

    # Test timeout behavior using the aiohttp branch (but requests would be similar).
    # Set a very small number of attempts
    monkeypatch.setattr(mod, "MAX_POLL_ATTEMPTS", 2)

    # aiohttp returns pending statuses and never success or error
    bodies = [{"status": "pending"}, {"status": "pending"}]
    fake_aio = _make_aiohttp_module(bodies)
    monkeypatch.setitem(sys.modules, "aiohttp", fake_aio)
    monkeypatch.setattr(asyncio, "sleep", _noop_sleep)

    with pytest.raises(TimeoutError) as exc:
        await provider._poll_for_result("req-id-timeout")
    assert "timed out" in str(exc.value)
