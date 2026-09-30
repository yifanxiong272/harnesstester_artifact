# file: browser_use/sync/auth.py:157-273
# asked: {"lines": [167, 169, 171, 172, 173, 174, 175, 176, 177, 178, 182, 183, 186, 187, 188, 191, 192, 193, 194, 197, 198, 199, 202, 203, 205, 207, 208, 209, 210, 213, 214, 216, 217, 219, 222, 223, 224, 225, 226, 227, 228, 229, 230, 234, 235, 238, 239, 240, 243, 244, 245, 246, 249, 250, 251, 254, 255, 257, 259, 260, 261, 262, 265, 266, 268, 269, 271, 273], "branches": [[169, 171], [169, 222], [171, 172], [171, 273], [182, 183], [182, 205], [186, 187], [186, 191], [191, 192], [191, 197], [197, 198], [197, 202], [202, 203], [202, 219], [205, 207], [205, 213], [208, 209], [208, 219], [223, 224], [223, 273], [234, 235], [234, 257], [238, 239], [238, 243], [243, 244], [243, 249], [249, 250], [249, 254], [254, 255], [254, 271], [257, 259], [257, 265], [260, 261], [260, 271]]}
# gained: {"lines": [167, 169, 171, 172, 173, 174, 175, 176, 177, 178, 182, 183, 186, 187, 188, 191, 192, 193, 194, 197, 198, 199, 202, 203, 205, 207, 208, 209, 210, 222, 223, 224, 225, 226, 227, 228, 229, 230, 234, 235, 238, 243, 249, 254, 255, 257, 259, 260, 261, 262, 268, 269, 271], "branches": [[169, 171], [169, 222], [171, 172], [182, 183], [182, 205], [186, 187], [186, 191], [191, 192], [191, 197], [197, 198], [197, 202], [202, 203], [205, 207], [208, 209], [223, 224], [234, 235], [234, 257], [238, 243], [243, 249], [249, 254], [254, 255], [257, 259], [260, 261]]}

import asyncio
import types
import pytest

import browser_use.sync.auth as auth_module


class FakeResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


class FakeHttpClient:
    def __init__(self, responses):
        # responses: list of either FakeResponse instances or Exception instances to raise
        self._responses = list(responses)
        self.calls = 0

    async def post(self, *args, **kwargs):
        self.calls += 1
        if not self._responses:
            # default: return a 400 Unknown error
            return FakeResponse(400, {"error": "unknown", "error_description": "no more responses"})
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeAsyncClient:
    def __init__(self, responses):
        self._client = FakeHttpClient(responses)

    async def __aenter__(self):
        return self._client

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _patch_common(monkeypatch):
    # Prevent side effects from DeviceAuthClient.__init__
    monkeypatch.setattr(auth_module, "get_or_create_device_id", lambda: "fake-device-id")
    # CloudAuthConfig must have load_from_file
    monkeypatch.setattr(
        auth_module,
        "CloudAuthConfig",
        types.SimpleNamespace(load_from_file=lambda: {"fake": "config"}),
    )
    # TEMP_USER_ID should exist
    monkeypatch.setattr(auth_module, "TEMP_USER_ID", "temp-user-id", raising=False)


@pytest.mark.parametrize("responses, expected", [
    # Single successful token response
    ([FakeResponse(200, {"access_token": "tok123"})], {"access_token": "tok123"}),
])
def test_poll_with_injected_client_access_token(monkeypatch, responses, expected):
    """
    Test the branch where an injected http_client is used and an access_token is returned immediately.
    """
    _patch_common(monkeypatch)

    fake_client = FakeHttpClient(responses)
    client = auth_module.DeviceAuthClient(base_url="https://api.example", http_client=fake_client)

    # Patch asyncio.sleep to avoid real delays
    async def dummy_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", dummy_sleep)

    result = asyncio.run(client.poll_for_token("devicecode", interval=0.001, timeout=1.0))
    assert result == expected


def test_poll_with_injected_client_pending_slowdown_then_error(monkeypatch):
    """
    Exercise the authorization_pending -> slow_down -> other error branch that prints and returns None.
    """
    _patch_common(monkeypatch)

    responses = [
        FakeResponse(200, {"error": "authorization_pending"}),
        FakeResponse(200, {"error": "slow_down", "interval": 0.0001}),
        FakeResponse(200, {"error": "some_error", "error_description": "boom"}),
    ]
    fake_client = FakeHttpClient(responses)
    client = auth_module.DeviceAuthClient(base_url="https://api.example", http_client=fake_client)

    async def dummy_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", dummy_sleep)

    result = asyncio.run(client.poll_for_token("devicecode", interval=0.001, timeout=1.0))
    assert result is None


def test_poll_with_injected_client_status_400_unexpected_error(monkeypatch):
    """
    Exercise the branch where a 400 is returned with an error not in ['authorization_pending','slow_down'].
    """
    _patch_common(monkeypatch)

    responses = [
        FakeResponse(400, {"error": "invalid_request", "error_description": "bad"}),
    ]
    fake_client = FakeHttpClient(responses)
    client = auth_module.DeviceAuthClient(base_url="https://api.example", http_client=fake_client)

    async def dummy_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", dummy_sleep)

    result = asyncio.run(client.poll_for_token("devicecode", interval=0.001, timeout=1.0))
    assert result is None


def test_poll_without_http_client_access_token(monkeypatch):
    """
    Patch httpx.AsyncClient used in the 'else' branch to return an access token via the context manager.
    """
    _patch_common(monkeypatch)

    responses = [FakeResponse(200, {"access_token": "ctx-tok"})]

    # Replace httpx.AsyncClient within the module to return our FakeAsyncClient
    def factory(*args, **kwargs):
        return FakeAsyncClient(list(responses))

    monkeypatch.setattr(auth_module.httpx, "AsyncClient", factory)

    async def dummy_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", dummy_sleep)

    client = auth_module.DeviceAuthClient(base_url="https://api.example", http_client=None)
    result = asyncio.run(client.poll_for_token("devicecode", interval=0.001, timeout=1.0))
    assert result == {"access_token": "ctx-tok"}


def test_poll_without_http_client_exception_then_timeout(monkeypatch):
    """
    Cause the post to raise an exception to cover the except branch, and ensure the loop eventually times out and returns None.
    """
    _patch_common(monkeypatch)

    # post will raise an exception on first call
    responses = [Exception("network fail")]

    def factory(*args, **kwargs):
        return FakeAsyncClient(list(responses))

    monkeypatch.setattr(auth_module.httpx, "AsyncClient", factory)

    # Patch asyncio.sleep to avoid delays
    async def dummy_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", dummy_sleep)

    # Make time.time increase slightly on each call so the loop terminates after a few iterations
    start = 1000.0
    step = 0.01
    counter = {"i": 0}

    def fake_time():
        # increment each call to simulate passage of time
        val = start + counter["i"] * step
        counter["i"] += 1
        return val

    monkeypatch.setattr(auth_module, "time", types.SimpleNamespace(time=fake_time))
    # Also patch the module-level time used via 'import time' in other places (if any)
    monkeypatch.setattr("time.time", fake_time, raising=False)

    client = auth_module.DeviceAuthClient(base_url="https://api.example", http_client=None)

    # Use a small timeout so function returns quickly
    result = asyncio.run(client.poll_for_token("devicecode", interval=0.001, timeout=0.02))
    assert result is None
