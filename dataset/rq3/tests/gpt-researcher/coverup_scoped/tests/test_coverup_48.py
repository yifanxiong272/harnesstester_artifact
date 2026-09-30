# file: gpt_researcher/llm_provider/image/modelslab_image_generator.py:203-228
# asked: {"lines": [205, 206, 208, 209, 211, 212, 213, 214, 215, 216, 218, 219, 222, 223, 225, 226, 228], "branches": [[222, 223], [222, 225], [225, 226], [225, 228]]}
# gained: {"lines": [205, 206, 208, 209, 211, 212, 213, 214, 215, 216, 218, 219, 222, 223, 225, 226, 228], "branches": [[222, 223], [222, 225], [225, 226], [225, 228]]}

import asyncio
import builtins
import types
import sys
import pytest

from gpt_researcher.llm_provider.image import modelslab_image_generator as mlmod


@pytest.mark.asyncio
async def test_aiohttp_returns_output(monkeypatch):
    # Create fake aiohttp module with async context managers
    aiohttp_mod = types.ModuleType("aiohttp")

    class ClientTimeout:
        def __init__(self, total=None):
            self.total = total

    class FakeResp:
        async def json(self):
            return {"output": ["img1", "img2"]}

    class FakePostCM:
        async def __aenter__(self):
            return FakeResp()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        def post(self, url, json, timeout):
            # validate parameters were passed through
            assert url == "http://test-text2img"
            assert isinstance(timeout, ClientTimeout)
            assert json == {"prompt": "hello"}
            return FakePostCM()

    class FakeClientSessionCM:
        async def __aenter__(self):
            return FakeSession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def ClientSession():
        return FakeClientSessionCM()

    aiohttp_mod.ClientTimeout = ClientTimeout
    aiohttp_mod.ClientSession = ClientSession

    # Inject fake module
    monkeypatch.setitem(sys.modules, "aiohttp", aiohttp_mod)

    # Ensure module under test uses a known URL
    monkeypatch.setattr(mlmod, "TEXT2IMG_URL", "http://test-text2img")

    provider = mlmod.ModelsLabImageGeneratorProvider()
    result = await provider._request_images({"prompt": "hello"})
    assert result == ["img1", "img2"]


@pytest.mark.asyncio
async def test_aiohttp_raises_runtime_error_on_error_status(monkeypatch):
    # Fake aiohttp that returns status error
    aiohttp_mod = types.ModuleType("aiohttp")

    class ClientTimeout:
        def __init__(self, total=None):
            self.total = total

    class FakeResp:
        async def json(self):
            return {"status": "error", "messege": "something went wrong"}

    class FakePostCM:
        async def __aenter__(self):
            return FakeResp()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        def post(self, url, json, timeout):
            return FakePostCM()

    class FakeClientSessionCM:
        async def __aenter__(self):
            return FakeSession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def ClientSession():
        return FakeClientSessionCM()

    aiohttp_mod.ClientTimeout = ClientTimeout
    aiohttp_mod.ClientSession = ClientSession

    monkeypatch.setitem(sys.modules, "aiohttp", aiohttp_mod)
    monkeypatch.setattr(mlmod, "TEXT2IMG_URL", "http://test-text2img")

    provider = mlmod.ModelsLabImageGeneratorProvider()
    with pytest.raises(RuntimeError) as excinfo:
        await provider._request_images({"prompt": "oops"})
    assert "something went wrong" in str(excinfo.value)


@pytest.mark.asyncio
async def test_requests_importerror_processing_calls_poll(monkeypatch):
    # Force ImportError for 'aiohttp' imports
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "aiohttp":
            raise ImportError("no aiohttp")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    # Create fake requests module
    requests_mod = types.ModuleType("requests")

    class FakeResponse:
        def __init__(self, body):
            self._body = body

        def json(self):
            return self._body

    def fake_post(url, json, timeout):
        assert url == "http://test-text2img"
        assert json == {"prompt": "process me"}
        assert timeout == 30
        # Simulate processing response
        return FakeResponse({"status": "processing", "id": "job123"})

    requests_mod.post = fake_post
    monkeypatch.setitem(sys.modules, "requests", requests_mod)

    # Monkeypatch asyncio.to_thread to run sync function immediately in test loop
    def fake_to_thread(fn, *args, **kwargs):
        # Execute the callable synchronously and return an awaitable Future with result
        loop = asyncio.get_event_loop()
        fut = loop.create_future()
        try:
            fut.set_result(fn())
        except Exception as e:
            fut.set_exception(e)
        return fut

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    monkeypatch.setattr(mlmod, "TEXT2IMG_URL", "http://test-text2img")

    provider = mlmod.ModelsLabImageGeneratorProvider()

    # Patch _poll_for_result to ensure it's called with the expected id and to return a result
    async def fake_poll(job_id):
        assert job_id == "job123"
        return ["polled_image"]

    monkeypatch.setattr(provider, "_poll_for_result", fake_poll)

    result = await provider._request_images({"prompt": "process me"})
    assert result == ["polled_image"]
