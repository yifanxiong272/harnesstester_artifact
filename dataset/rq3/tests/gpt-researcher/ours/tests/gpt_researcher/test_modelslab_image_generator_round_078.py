import asyncio
import builtins
import sys
import types
import pytest
from types import ModuleType

from gpt_researcher.llm_provider.image.modelslab_image_generator import (
    ModelsLabImageGeneratorProvider,
)

# Helper to create a fake aiohttp module exposing ClientSession and ClientTimeout
def _make_fake_aiohttp_module(body):
    mod = ModuleType("aiohttp")

    class FakeResp:
        def __init__(self, body):
            self._body = body

        async def json(self):
            # mimic aiohttp's resp.json() async method
            return self._body

    class FakePostCtx:
        def __init__(self, resp):
            self._resp = resp

        async def __aenter__(self):
            return self._resp

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        def __init__(self, body):
            self._body = body

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json=None, timeout=None):
            # return an async context manager that yields a FakeResp
            return FakePostCtx(FakeResp(self._body))

    class FakeClientSession:
        def __init__(self, *args, **kwargs):
            self._body = body

        def __call__(self, *args, **kwargs):
            return FakeSession(self._body)

        async def __aenter__(self):
            return FakeSession(self._body)

        async def __aexit__(self, exc_type, exc, tb):
            return False

    # ClientSession needs to be callable as a context manager when imported and used
    def ClientSession(*args, **kwargs):
        return FakeSession(body)

    class ClientTimeout:
        def __init__(self, total=None):
            self.total = total

    mod.ClientSession = ClientSession
    mod.ClientTimeout = ClientTimeout
    return mod


@pytest.mark.asyncio
async def test_request_images_aiohttp_error_round_078(monkeypatch):
    """When aiohttp is present and the API returns status 'error', a RuntimeError with the provided 'messege' is raised."""
    body = {"status": "error", "messege": "boom-error"}
    fake_aio = _make_fake_aiohttp_module(body)
    # Insert fake aiohttp into sys.modules so the in-function `import aiohttp` gets it
    monkeypatch.setitem(sys.modules, "aiohttp", fake_aio)

    # Create an uninitialized instance to avoid __init__ side-effects
    inst = object.__new__(ModelsLabImageGeneratorProvider)

    with pytest.raises(RuntimeError) as excinfo:
        await inst._request_images({"prompt": "x"})

    # Ensure the error message uses the misspelled 'messege' key from the body
    assert "boom-error" in str(excinfo.value)


@pytest.mark.asyncio
async def test_request_images_importerror_processing_round_078(monkeypatch):
    """When importing aiohttp fails, the code falls back to requests and, if status is 'processing' and id present, polls for result."""
    # Make builtins.__import__ raise ImportError for 'aiohttp' only
    real_import = builtins.__import__

    def custom_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "aiohttp":
            raise ImportError("no aiohttp here")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", custom_import)

    # Provide a fake requests module so the fallback path doesn't perform network IO
    fake_requests = ModuleType("requests")

    class FakeResp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            # requests.Response.json is synchronous
            return self._payload

    def fake_post(url, json=None, timeout=None):
        return FakeResp({"status": "processing", "id": "req-123"})

    fake_requests.post = fake_post
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    inst = object.__new__(ModelsLabImageGeneratorProvider)

    # Patch instance._poll_for_result to verify it's called and return a deterministic value
    async def fake_poll(self, request_id):
        assert request_id == "req-123"
        return ["polled-result.png"]

    # bind method to instance
    monkeypatch.setattr(inst, "_poll_for_result", types.MethodType(fake_poll, inst))

    result = await inst._request_images({"prompt": "y"})
    assert result == ["polled-result.png"]


@pytest.mark.asyncio
async def test_request_images_output_round_078(monkeypatch):
    """When API returns an 'output' list (neither error nor processing), _request_images returns that list."""
    body = {"output": ["one.png", "two.png"]}
    fake_aio = _make_fake_aiohttp_module(body)
    monkeypatch.setitem(sys.modules, "aiohttp", fake_aio)

    inst = object.__new__(ModelsLabImageGeneratorProvider)
    result = await inst._request_images({"prompt": "z"})
    assert result == ["one.png", "two.png"]
