import asyncio
import builtins
import sys
from types import ModuleType

import pytest

from gpt_researcher.llm_provider.image.modelslab_image_generator import (
    ModelsLabImageGeneratorProvider,
)


def _make_fake_aiohttp_module(expected_bytes=b"aio-data"):
    mod = ModuleType("aiohttp")

    class FakeResponse:
        def __init__(self, data):
            self._data = data

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self):
            # emulate successful status
            return None

        async def read(self):
            return self._data

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, url, timeout=None):
            # return an async context manager-like response
            return FakeResponse(expected_bytes + b"-" + url.encode())

    class ClientTimeout:
        def __init__(self, total=None):
            # record for assertion
            mod._last_timeout = total

    def ClientSession():
        return FakeSession()

    mod.ClientSession = ClientSession
    mod.ClientTimeout = ClientTimeout
    return mod


def _make_fake_requests_module(response_bytes=b"req-data"):
    mod = ModuleType("requests")

    class FakeResponse:
        def __init__(self, data):
            self.content = data

        def raise_for_status(self):
            return None

    def get(url, timeout=None):
        return FakeResponse(response_bytes + b"-" + url.encode())

    mod.get = get
    return mod


def test_download_image_uses_aiohttp_round_127(monkeypatch, tmp_path):
    """When aiohttp is available, _download_image should use it and return bytes."""
    fake_bytes = b"IMG-HTTP"
    fake_aio = _make_fake_aiohttp_module(expected_bytes=fake_bytes)

    # Inject fake aiohttp module so 'import aiohttp' inside the function gets it
    monkeypatch.setitem(sys.modules, "aiohttp", fake_aio)

    # Provide a valid output_dir to avoid Path(None) error
    prov = ModelsLabImageGeneratorProvider(model_id="m", api_key="k", output_dir=str(tmp_path))
    url = "http://example.com/image.png"

    # Run the async function synchronously in the test
    result = asyncio.run(prov._download_image(url))

    # The fake returns expected_bytes + '-' + url.encode()
    assert result == fake_bytes + b"-" + url.encode()

    # Ensure ClientTimeout saw total=30
    assert getattr(fake_aio, "_last_timeout") == 30


def test_download_image_fallback_requests_round_127(monkeypatch, tmp_path):
    """If importing aiohttp raises ImportError, the function should fall back to requests via asyncio.to_thread."""
    # Make sure importing aiohttp raises ImportError
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "aiohttp":
            raise ImportError("no aiohttp")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    # Provide a fake requests module that has get returning object with content
    fake_requests = _make_fake_requests_module(response_bytes=b"REQ-IMG")
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    # Patch asyncio.to_thread to avoid real threading; emulate awaiting of result
    async def fake_to_thread(func, *args, **kwargs):
        # call synchronously
        return func(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    prov = ModelsLabImageGeneratorProvider(model_id="m", api_key="k", output_dir=str(tmp_path))
    url = "http://example.com/fallback.png"

    result = asyncio.run(prov._download_image(url))

    # The fake requests.get returns response.content as response_bytes + '-' + url.encode()
    assert result == b"REQ-IMG" + b"-" + url.encode()
