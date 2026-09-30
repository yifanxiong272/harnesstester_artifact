import asyncio
import httpx
import pytest

import openhands.integrations.gitlab.service.base as base_module
from openhands.integrations.gitlab.service.base import GitLabMixinBase

# Dummy async context manager used to replace httpx.AsyncClient inside the module
class DummyAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyResponse:
    def __init__(self, status_code=200, headers=None, json_data=None, text_data=""):
        self.status_code = status_code
        self.headers = headers or {}
        self._json = json_data
        self.text = text_data
        # allow injecting an exception to raise from raise_for_status
        self._raise_exc = None

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc

    def json(self):
        return self._json


@pytest.mark.asyncio
async def test_make_request_json_with_headers_round_064(monkeypatch):
    """
    Cover path where no token refresh is needed, headers include Link and X-Total,
    and content-type contains application/json so response.json() is returned.
    """
    # Patch the AsyncClient used in the module to avoid real network calls
    monkeypatch.setattr(base_module.httpx, "AsyncClient", DummyAsyncClient)

    # Build a dummy self object with the methods/attributes used by _make_request
    class DummySelf:
        pass

    inst = DummySelf()
    inst.refresh = False

    async def _get_headers():
        return {"Authorization": "token-123"}

    async def execute_request(client, url, headers, params, method):
        # return a response that looks like a successful JSON response with pagination headers
        return DummyResponse(
            status_code=200,
            headers={
                "Link": "<https://api/page2>; rel=next",
                "X-Total": "42",
                "Content-Type": "application/json; charset=utf-8",
            },
            json_data={"ok": True},
            text_data="irrelevant",
        )

    # provide required attributes and methods
    inst._get_headers = _get_headers
    inst.execute_request = execute_request

    # not needed but present
    async def get_latest_token():
        raise AssertionError("should not be called in this scenario")

    inst.get_latest_token = get_latest_token

    def _has_token_expired(status_code):
        return False

    inst._has_token_expired = _has_token_expired

    # error handlers if ever called
    def handle_http_status_error(e):
        return e

    def handle_http_error(e):
        return e

    inst.handle_http_status_error = handle_http_status_error
    inst.handle_http_error = handle_http_error

    # Call the function under test
    result_value, result_headers = await GitLabMixinBase._make_request(
        inst, url="https://example.local/api/resource", params=None
    )

    assert result_value == {"ok": True}
    # ensure both pagination headers propagated
    assert result_headers["Link"] == "<https://api/page2>; rel=next"
    assert result_headers["X-Total"] == "42"


@pytest.mark.asyncio
async def test_make_request_refresh_token_then_text_round_064(monkeypatch):
    """
    Cover path where refresh is True and the first response indicates expired token,
    causing get_latest_token to be called and the request retried.
    Also cover the non-JSON content-type branch returning response.text.
    """
    monkeypatch.setattr(base_module.httpx, "AsyncClient", DummyAsyncClient)

    class DummySelf:
        pass

    inst = DummySelf()
    inst.refresh = True

    # We'll simulate execute_request being called twice: first returns expired token,
    # second returns a text response.
    call_count = {"n": 0}

    async def _get_headers():
        # return a header that could change after refresh, but function does not inspect it deeply
        return {"Authorization": f"token-{call_count['n']}"}

    async def execute_request(client, url, headers, params, method):
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            # first response indicates expired token (status 401)
            return DummyResponse(status_code=401, headers={"Content-Type": "text/plain"}, text_data="expired")
        else:
            # second response is successful and returns plain text
            return DummyResponse(status_code=200, headers={"Content-Type": "text/plain"}, text_data="ok-after-refresh")

    async def get_latest_token():
        # mark that it's been called by setting an attribute
        inst._refreshed = True

    def _has_token_expired(status_code):
        # treat any 401 as expired (for first call), otherwise not expired
        return status_code == 401

    inst._get_headers = _get_headers
    inst.execute_request = execute_request
    inst.get_latest_token = get_latest_token
    inst._has_token_expired = _has_token_expired

    # handlers should not be invoked in this success path
    inst.handle_http_status_error = lambda e: e
    inst.handle_http_error = lambda e: e

    val, headers = await GitLabMixinBase._make_request(inst, url="/retry-test")

    assert getattr(inst, "_refreshed", False) is True
    assert val == "ok-after-refresh"
    # X-Total not present in this response; headers should be empty dict
    assert headers == {}


@pytest.mark.asyncio
async def test_make_request_raises_http_status_error_round_064(monkeypatch):
    """
    Cover the branch where response.raise_for_status() raises an httpx.HTTPStatusError,
    and ensure the exception returned by handle_http_status_error is raised.
    """
    monkeypatch.setattr(base_module.httpx, "AsyncClient", DummyAsyncClient)

    class DummySelf:
        pass

    inst = DummySelf()
    inst.refresh = False

    async def _get_headers():
        return {"Authorization": "x"}

    async def execute_request(client, url, headers, params, method):
        resp = DummyResponse(status_code=500, headers={"Content-Type": "application/json"})
        # make raise_for_status raise an httpx.HTTPStatusError
        resp._raise_exc = httpx.HTTPStatusError("fail", request=None, response=None)
        return resp

    inst._get_headers = _get_headers
    inst.execute_request = execute_request

    # when the exception is handled by the instance, return a ValueError to be raised
    captured = {"seen": None}

    def handle_http_status_error(e):
        captured["seen"] = e
        return ValueError("mapped-status-error")

    inst.handle_http_status_error = handle_http_status_error
    inst.handle_http_error = lambda e: e
    inst._has_token_expired = lambda code: False

    with pytest.raises(ValueError) as ei:
        await GitLabMixinBase._make_request(inst, url="/error-status")

    assert str(ei.value) == "mapped-status-error"
    # ensure original HTTPStatusError was passed to the handler
    assert isinstance(captured["seen"], httpx.HTTPStatusError)


@pytest.mark.asyncio
async def test_make_request_raises_http_error_round_064(monkeypatch):
    """
    Cover the branch where an httpx.HTTPError is raised during the request and ensure
    handle_http_error result is raised by _make_request.
    """
    monkeypatch.setattr(base_module.httpx, "AsyncClient", DummyAsyncClient)

    class DummySelf:
        pass

    inst = DummySelf()
    inst.refresh = False

    async def _get_headers():
        return {"Authorization": "x"}

    async def execute_request(client, url, headers, params, method):
        # Simulate a lower-level HTTP error during request execution
        raise httpx.HTTPError("connection failed")

    inst._get_headers = _get_headers
    inst.execute_request = execute_request
    inst._has_token_expired = lambda code: False

    def handle_http_error(e):
        # map to a distinct runtime error so we can assert it was raised
        return RuntimeError("mapped-http-error")

    inst.handle_http_error = handle_http_error
    inst.handle_http_status_error = lambda e: e

    with pytest.raises(RuntimeError) as excinfo:
        await GitLabMixinBase._make_request(inst, url="/raise-http-error")

    assert str(excinfo.value) == "mapped-http-error"
