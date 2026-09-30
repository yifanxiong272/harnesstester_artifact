import builtins
import sys
import types
import asyncio
import pytest

from gpt_researcher.llm_provider.image import modelslab_image_generator as mg

# Helper async no-op sleep to speed polling loops
async def _no_sleep(_):
    return None

@pytest.mark.asyncio
async def test_aiohttp_success_round_034(monkeypatch):
    # Arrange: ensure aiohttp is importable and provides an async ClientSession
    body = {"status": "success", "output": ["img1.png"]}

    class FakeResp:
        def __init__(self, payload):
            self._payload = payload

        async def json(self):
            return self._payload

    class FakePostCtx:
        def __init__(self, payload):
            self._payload = payload

        async def __aenter__(self):
            return FakeResp(self._payload)

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        def __init__(self, payload):
            self._payload = payload

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return FakePostCtx(self._payload)

    aio_mod = types.ModuleType("aiohttp")
    aio_mod.ClientSession = lambda: FakeSession(body)
    aio_mod.ClientTimeout = lambda total=None: None
    monkeypatch.setitem(sys.modules, "aiohttp", aio_mod)

    # Patch timing and loop parameters to be deterministic/fast
    monkeypatch.setattr(mg, "MAX_POLL_ATTEMPTS", 1)
    monkeypatch.setattr(mg, "POLL_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    provider = mg.ModelsLabImageGeneratorProvider(model_id="m", api_key="k", output_dir="out")

    # Act
    result = await provider._poll_for_result("request-id-1")

    # Assert
    assert result == ["img1.png"]


@pytest.mark.asyncio
async def test_aiohttp_error_round_034(monkeypatch):
    # Arrange: aiohttp returning an error status without 'messege' key
    body = {"status": "error"}

    class FakeResp:
        def __init__(self, payload):
            self._payload = payload

        async def json(self):
            return self._payload

    class FakePostCtx:
        def __init__(self, payload):
            self._payload = payload

        async def __aenter__(self):
            return FakeResp(self._payload)

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        def __init__(self, payload):
            self._payload = payload

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return FakePostCtx(self._payload)

    aio_mod = types.ModuleType("aiohttp")
    aio_mod.ClientSession = lambda: FakeSession(body)
    aio_mod.ClientTimeout = lambda total=None: None
    monkeypatch.setitem(sys.modules, "aiohttp", aio_mod)

    monkeypatch.setattr(mg, "MAX_POLL_ATTEMPTS", 1)
    monkeypatch.setattr(mg, "POLL_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    provider = mg.ModelsLabImageGeneratorProvider(model_id="m", api_key="k", output_dir="out")

    # Act / Assert: should raise RuntimeError with default message
    with pytest.raises(RuntimeError) as exc:
        await provider._poll_for_result("request-id-err")

    assert "ModelsLab generation error" in str(exc.value)


@pytest.mark.asyncio
async def test_requests_success_round_034(monkeypatch):
    # Arrange: force ImportError when attempting to import aiohttp
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "aiohttp":
            raise ImportError("no aiohttp")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    # Patch asyncio.sleep to no-op and to_thread to call sync function directly
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    async def fake_to_thread(func, *a, **k):
        return func(*a, **k)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    # Provide a synchronous requests.post replacement
    class SyncResp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    def fake_requests_post(url, json=None, timeout=None):
        return SyncResp({"status": "success", "output": ["rimg.png"]})

    # Patch requests module in sys.modules to be used by the code
    req_mod = types.ModuleType("requests")
    req_mod.post = fake_requests_post
    monkeypatch.setitem(sys.modules, "requests", req_mod)

    monkeypatch.setattr(mg, "MAX_POLL_ATTEMPTS", 1)
    monkeypatch.setattr(mg, "POLL_INTERVAL_SECONDS", 0)

    provider = mg.ModelsLabImageGeneratorProvider(model_id="m", api_key="k", output_dir="out")

    # Act
    result = await provider._poll_for_result("request-id-req")

    # Assert
    assert result == ["rimg.png"]


@pytest.mark.asyncio
async def test_requests_error_round_034(monkeypatch):
    # Arrange: make 'aiohttp' import fail
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "aiohttp":
            raise ImportError("no aiohttp")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    async def fake_to_thread(func, *a, **k):
        return func(*a, **k)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    class SyncResp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    def fake_requests_post(url, json=None, timeout=None):
        return SyncResp({"status": "error"})

    req_mod = types.ModuleType("requests")
    req_mod.post = fake_requests_post
    monkeypatch.setitem(sys.modules, "requests", req_mod)

    monkeypatch.setattr(mg, "MAX_POLL_ATTEMPTS", 1)
    monkeypatch.setattr(mg, "POLL_INTERVAL_SECONDS", 0)

    provider = mg.ModelsLabImageGeneratorProvider(model_id="m", api_key="k", output_dir="out")

    # Act / Assert
    with pytest.raises(RuntimeError) as exc:
        await provider._poll_for_result("request-id-req-err")

    assert "ModelsLab generation error" in str(exc.value)


@pytest.mark.asyncio
async def test_aiohttp_timeout_round_034(monkeypatch):
    # Arrange: aiohttp present but returns a pending status => should timeout
    body = {"status": "pending"}

    class FakeResp:
        def __init__(self, payload):
            self._payload = payload

        async def json(self):
            return self._payload

    class FakePostCtx:
        def __init__(self, payload):
            self._payload = payload

        async def __aenter__(self):
            return FakeResp(self._payload)

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        def __init__(self, payload):
            self._payload = payload

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return FakePostCtx(self._payload)

    aio_mod = types.ModuleType("aiohttp")
    aio_mod.ClientSession = lambda: FakeSession(body)
    aio_mod.ClientTimeout = lambda total=None: None
    monkeypatch.setitem(sys.modules, "aiohttp", aio_mod)

    # one attempt only -> should raise TimeoutError after loop
    monkeypatch.setattr(mg, "MAX_POLL_ATTEMPTS", 1)
    monkeypatch.setattr(mg, "POLL_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    provider = mg.ModelsLabImageGeneratorProvider(model_id="m", api_key="k", output_dir="out")

    with pytest.raises(TimeoutError):
        await provider._poll_for_result("request-id-timeout")
