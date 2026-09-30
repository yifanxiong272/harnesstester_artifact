import pytest
import types
import httpx

from openhands.integrations.gitlab.service import base as base_mod
from openhands.integrations.gitlab.service.base import GitLabMixinBase

# Helpers to build fake responses
class FakeResponse:
    def __init__(self, status_code=200, headers=None, json_body=None, text_body=""):
        self.status_code = status_code
        self.headers = headers or {}
        self._json_body = json_body
        self.text = text_body

    def json(self):
        return self._json_body

    def raise_for_status(self):
        # Raise nothing for 2xx, raise HTTPStatusError for other codes
        if 200 <= self.status_code < 300:
            return None
        raise httpx.HTTPStatusError("status error", request=None, response=None)


class DummyAsyncClient:
    def __init__(self, *args, **kwargs):
        # placeholder to mimic httpx.AsyncClient signature
        pass

    async def __aenter__(self):
        # return an object that would be passed to execute_request
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


# Minimal concrete implementations for abstract methods used by BaseGitService
class AbstractStubsMixin:
    def _get_cursorrules_url(self):
        return ""

    def _get_file_name_from_item(self, item):
        return ""

    def _get_file_path_from_item(self, item):
        return ""

    def _get_microagents_directory_params(self):
        return {}

    def _get_microagents_directory_url(self):
        return ""

    def _is_valid_microagent_file(self, filename):
        return False


@pytest.mark.asyncio
async def test_json_with_refresh_round_064(monkeypatch):
    """
    - Simulate initial 401 response causing token refresh path to run.
    - Ensure get_latest_token is awaited and second request's JSON + headers are returned.
    """
    # Patch AsyncClient and verify option used by the module under test
    monkeypatch.setattr(base_mod, "httpx", types.SimpleNamespace(AsyncClient=DummyAsyncClient, HTTPStatusError=httpx.HTTPStatusError, HTTPError=httpx.HTTPError))
    monkeypatch.setattr(base_mod, "httpx_verify_option", lambda: False)

    # Create a dummy service subclass that overrides only what's needed
    class DummyService(AbstractStubsMixin, GitLabMixinBase):
        def __init__(self):
            # do not call any parent init
            self._call_count = 0
            self.refresh = True
            self.latest_token_fetched = False

        async def _get_headers(self):
            # Always return some headers; after token refresh this could be same for test simplicity
            return {"Authorization": "token"}

        async def get_latest_token(self):
            self.latest_token_fetched = True

        def _has_token_expired(self, status_code):
            # token is considered expired for 401 only
            return status_code == 401

        async def execute_request(self, *, client, url, headers, params, method):
            # Return a 401 first, then a 200 with json and Link/X-Total headers
            self._call_count += 1
            if self._call_count == 1:
                return FakeResponse(status_code=401, headers={"Content-Type": "application/json"}, json_body={"retry": True})
            return FakeResponse(
                status_code=200,
                headers={"Content-Type": "application/json", "Link": "<next>", "X-Total": "5"},
                json_body={"ok": True},
            )

        def handle_http_status_error(self, e):
            # Not expected in this test
            return e

        def handle_http_error(self, e):
            # Not expected in this test
            return e

    svc = DummyService()

    result, headers = await svc._make_request(url="http://example", params=None, method=base_mod.RequestMethod.GET)

    # After refresh, latest token must have been fetched and returned value should be from second response
    assert svc.latest_token_fetched is True
    assert result == {"ok": True}
    # Headers should include Link and X-Total as set on second response
    assert headers == {"Link": "<next>", "X-Total": "5"}


@pytest.mark.asyncio
async def test_text_no_refresh_round_064(monkeypatch):
    """
    - Ensure plain text responses (no application/json in Content-Type) return .text
    - Ensure when self.refresh is False the token refresh branch is not executed
    """
    monkeypatch.setattr(base_mod, "httpx", types.SimpleNamespace(AsyncClient=DummyAsyncClient, HTTPStatusError=httpx.HTTPStatusError, HTTPError=httpx.HTTPError))
    monkeypatch.setattr(base_mod, "httpx_verify_option", lambda: True)

    class DummyServiceNoRefresh(AbstractStubsMixin, GitLabMixinBase):
        def __init__(self):
            self.refresh = False

        async def _get_headers(self):
            return {"Authorization": "token"}

        async def execute_request(self, *, client, url, headers, params, method):
            return FakeResponse(status_code=200, headers={"Content-Type": "text/plain"}, text_body="plain text")

        def _has_token_expired(self, status_code):
            # should not be called in this scenario
            raise AssertionError("_has_token_expired should not be called when refresh is False")

        def handle_http_status_error(self, e):
            return e

        def handle_http_error(self, e):
            return e

    svc = DummyServiceNoRefresh()

    result, headers = await svc._make_request(url="http://example", params=None, method=base_mod.RequestMethod.GET)

    assert result == "plain text"
    assert headers == {}


@pytest.mark.asyncio
async def test_http_status_error_round_064(monkeypatch):
    """
    - Simulate response.raise_for_status raising httpx.HTTPStatusError and ensure
      handle_http_status_error return value is raised by _make_request.
    """
    # Keep httpx exceptions visible from module
    monkeypatch.setattr(base_mod, "httpx", types.SimpleNamespace(AsyncClient=DummyAsyncClient, HTTPStatusError=httpx.HTTPStatusError, HTTPError=httpx.HTTPError))
    monkeypatch.setattr(base_mod, "httpx_verify_option", lambda: True)

    class DummyServiceStatusErr(AbstractStubsMixin, GitLabMixinBase):
        def __init__(self):
            self.refresh = False
            self.handled = False

        async def _get_headers(self):
            return {}

        async def execute_request(self, *, client, url, headers, params, method):
            # Return a response whose raise_for_status will raise
            return FakeResponse(status_code=500, headers={"Content-Type": "application/json"}, json_body={})

        def handle_http_status_error(self, e):
            self.handled = True
            # Return an exception to be raised by the caller (as per code: raise self.handle_http_status_error(e))
            return ValueError("handled status error")

        def handle_http_error(self, e):
            return e

    svc = DummyServiceStatusErr()

    with pytest.raises(ValueError) as excinfo:
        await svc._make_request(url="http://example", params=None, method=base_mod.RequestMethod.GET)

    assert "handled status error" in str(excinfo.value)
    assert svc.handled is True


@pytest.mark.asyncio
async def test_http_error_round_064(monkeypatch):
    """
    - Simulate execute_request raising a lower-level httpx.HTTPError and ensure
      handle_http_error is invoked and its returned exception is raised.
    """
    monkeypatch.setattr(base_mod, "httpx", types.SimpleNamespace(AsyncClient=DummyAsyncClient, HTTPStatusError=httpx.HTTPStatusError, HTTPError=httpx.HTTPError))
    monkeypatch.setattr(base_mod, "httpx_verify_option", lambda: True)

    class DummyServiceHttpErr(AbstractStubsMixin, GitLabMixinBase):
        def __init__(self):
            self.refresh = False
            self.handled = False

        async def _get_headers(self):
            return {}

        async def execute_request(self, *, client, url, headers, params, method):
            raise httpx.HTTPError("network down")

        def handle_http_error(self, e):
            self.handled = True
            return RuntimeError("handled network")

        def handle_http_status_error(self, e):
            return e

    svc = DummyServiceHttpErr()

    with pytest.raises(RuntimeError) as excinfo:
        await svc._make_request(url="http://example", params=None, method=base_mod.RequestMethod.GET)

    assert "handled network" in str(excinfo.value)
    assert svc.handled is True
