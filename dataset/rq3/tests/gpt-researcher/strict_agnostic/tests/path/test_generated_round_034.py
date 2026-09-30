import asyncio
import importlib
import sys
import types
import builtins
import pytest

MODULE_PATH = "gpt_researcher.llm_provider.image.modelslab_image_generator"

# Helper to build a fake aiohttp module with configurable response JSON
def make_fake_aiohttp(response_json_sequence):
    """Return a fake aiohttp module object that yields responses from the provided sequence.

    response_json_sequence: an iterator or list of dicts that will be returned from resp.json()
    """
    seq = iter(response_json_sequence)

    class FakeResp:
        async def json(self):
            try:
                return next(seq)
            except StopIteration:
                # If sequence exhausted, keep returning the last value
                return response_json_sequence[-1]

    class PostCtx:
        def __init__(self, resp):
            self._resp = resp

        async def __aenter__(self):
            return self._resp

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class ClientSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return PostCtx(FakeResp())

    class ClientTimeout:
        def __init__(self, total=None):
            self.total = total

    fake = types.SimpleNamespace(
        ClientSession=ClientSession,
        ClientTimeout=ClientTimeout,
    )
    return fake


# Helper to build a fake requests module where post returns an object with .json()
def make_fake_requests(response_json_sequence):
    seq = iter(response_json_sequence)

    class FakeResp:
        def json(self):
            try:
                return next(seq)
            except StopIteration:
                return response_json_sequence[-1]

    def post(*args, **kwargs):
        return FakeResp()

    fake = types.SimpleNamespace(post=post)
    return fake


@pytest.mark.asyncio
async def test_aiohttp_success_returns_output_round_034(monkeypatch):
    """When aiohttp is available and returns status=success with output, _poll_for_result returns that output."""
    mod = importlib.import_module(MODULE_PATH)

    # Ensure fast deterministic loop
    monkeypatch.setattr(mod, "MAX_POLL_ATTEMPTS", 1)
    monkeypatch.setattr(mod, "POLL_INTERVAL_SECONDS", 0)

    # Patch asyncio.sleep to a no-op async function
    async def _nosleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)

    # Provide fake aiohttp that yields a success response
    fake_aio = make_fake_aiohttp([{"status": "success", "output": ["img_aio"]}])
    monkeypatch.setitem(sys.modules, "aiohttp", fake_aio)

    provider = mod.ModelsLabImageGeneratorProvider("model", "apikey", "outdir")

    result = await provider._poll_for_result("request-id-1")

    assert result == ["img_aio"]


@pytest.mark.asyncio
async def test_aiohttp_error_raises_runtime_round_034(monkeypatch):
    """When aiohttp returns status=error with a 'messege', the function raises RuntimeError with that message."""
    mod = importlib.import_module(MODULE_PATH)

    monkeypatch.setattr(mod, "MAX_POLL_ATTEMPTS", 1)
    monkeypatch.setattr(mod, "POLL_INTERVAL_SECONDS", 0)

    async def _nosleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)

    fake_aio = make_fake_aiohttp([{"status": "error", "messege": "bad things"}])
    monkeypatch.setitem(sys.modules, "aiohttp", fake_aio)

    provider = mod.ModelsLabImageGeneratorProvider("m", "k", "o")

    with pytest.raises(RuntimeError) as exc:
        await provider._poll_for_result("rid")

    assert "bad things" in str(exc.value)


@pytest.mark.asyncio
async def test_aiohttp_timeout_raises_timeouterror_round_034(monkeypatch):
    """When aiohttp returns non-terminal status and attempts are exhausted, TimeoutError is raised."""
    mod = importlib.import_module(MODULE_PATH)

    # Force only one attempt so the test is quick
    monkeypatch.setattr(mod, "MAX_POLL_ATTEMPTS", 1)
    monkeypatch.setattr(mod, "POLL_INTERVAL_SECONDS", 0)

    async def _nosleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)

    # Return a 'pending' status (no success, no error)
    fake_aio = make_fake_aiohttp([{"status": "pending"}])
    monkeypatch.setitem(sys.modules, "aiohttp", fake_aio)

    provider = mod.ModelsLabImageGeneratorProvider("m", "k", "o")

    with pytest.raises(TimeoutError):
        await provider._poll_for_result("rid-timeout")


@pytest.mark.asyncio
async def test_requests_success_and_error_round_034(monkeypatch):
    """Test the fallback path when aiohttp is not importable: success returns output, error raises RuntimeError.

    We run both a success and an error scenario by swapping the fake requests responses.
    """
    mod = importlib.import_module(MODULE_PATH)

    # Force ImportError when attempting to import aiohttp by patching builtins.__import__
    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        # Intercept attempts to import aiohttp (top-level or submodule)
        if name == "aiohttp" or (isinstance(name, str) and name.split(".")[0] == "aiohttp"):
            raise ImportError("no aiohttp")
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    # Make loop tiny and no sleeping
    monkeypatch.setattr(mod, "MAX_POLL_ATTEMPTS", 1)
    monkeypatch.setattr(mod, "POLL_INTERVAL_SECONDS", 0)

    async def _nosleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", _nosleep)

    # Replace asyncio.to_thread with a direct synchronous call for determinism
    async def to_thread_sync(func, *a, **k):
        # emulate the real behavior: return the function's return value
        return func(*a, **k)

    monkeypatch.setattr(asyncio, "to_thread", to_thread_sync)

    # Success scenario
    fake_requests_success = make_fake_requests([{"status": "success", "output": ["img_req"]}])
    monkeypatch.setitem(sys.modules, "requests", fake_requests_success)

    provider = mod.ModelsLabImageGeneratorProvider("m", "k", "o")
    result = await provider._poll_for_result("rid-req-success")
    assert result == ["img_req"]

    # Error scenario: patch requests to return error with 'messege'
    fake_requests_error = make_fake_requests([{"status": "error", "messege": "req boom"}])
    monkeypatch.setitem(sys.modules, "requests", fake_requests_error)

    with pytest.raises(RuntimeError) as exc2:
        await provider._poll_for_result("rid-req-error")
    assert "req boom" in str(exc2.value)
