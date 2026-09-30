import importlib
import pytest

# Load the module under test
base_mod = importlib.import_module("openhands.integrations.gitlab.service.base")
GitLabMixinBase = base_mod.GitLabMixinBase

# Create a fake httpx replacement to avoid importing the real httpx and to control exceptions
class FakeHTTPX:
    class HTTPStatusError(Exception):
        pass

    class HTTPError(Exception):
        pass

    class AsyncClient:
        def __init__(self, verify=None):
            # Accept the verify arg used by the code under test
            self.verify = verify

        async def __aenter__(self):
            return "fake-client"

        async def __aexit__(self, exc_type, exc, tb):
            return False


# Simple fake Response object used by the tests
class FakeResponse:
    def __init__(self, status_code=200, headers=None, json_data=None, text_data=""):
        self.status_code = status_code
        self.headers = headers or {}
        self._json = json_data
        self.text = text_data

    def json(self):
        return self._json

    def raise_for_status(self):
        # Raise the module-level HTTPStatusError (which will be patched into the base module)
        if self.status_code >= 400:
            # The code under test expects httpx.HTTPStatusError from the module-level httpx
            raise base_mod.httpx.HTTPStatusError("status error")


# A testing subclass that provides the methods used by _make_request
class TestService(GitLabMixinBase):
    def __init__(self, responses):
        # Do not call super().__init__ to avoid base initialization; we override required behavior instead
        self._responses = list(responses)
        # Allow token refresh handling to be enabled/disabled
        self.refresh = True
        self._token_calls = 0

    async def _get_headers(self):
        # Return a predictable header for each call
        return {"Authorization": "token-v1"}

    async def get_latest_token(self):
        # Simulate refreshing token
        self._token_calls += 1

    def _has_token_expired(self, status_code):
        # Simple expiration predicate used by tests: 401 means expired
        return status_code == 401

    async def execute_request(self, client, url, headers, params, method):
        # Return pre-seeded responses or raise an exception if a real exception object is present
        if not self._responses:
            raise RuntimeError("No more responses configured")
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def handle_http_status_error(self, e):
        # Return an exception instance that the caller will raise
        return ValueError("handled status error")

    def handle_http_error(self, e):
        return KeyError("handled http error")

    # --- Minimal stubs for abstract methods required by the base class ---
    # The test previously failed because GitLabMixinBase had abstract methods that
    # prevented instantiation. Provide harmless implementations so the test can run.
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
async def test_make_request_no_refresh_json_round_064(monkeypatch):
    """
    - Patch module httpx to a fake one and httpx_verify_option to a deterministic value.
    - Provide a single 200 JSON response containing Link and X-Total headers.
    - Ensure returned payload is the JSON object and headers include Link and X-Total.
    """
    # Patch the module-level httpx and httpx_verify_option
    monkeypatch.setattr(base_mod, "httpx", FakeHTTPX)
    monkeypatch.setattr(base_mod, "httpx_verify_option", lambda: True)

    # Build a response with JSON content and Link/X-Total headers
    resp = FakeResponse(
        status_code=200,
        headers={"Link": "<https://api?page=2>; rel=\"next\"", "X-Total": "42", "Content-Type": "application/json"},
        json_data={"ok": True},
        text_data="should-not-be-used",
    )

    svc = TestService([resp])
    # Disable refresh path for this test
    svc.refresh = False

    result, headers = await svc._make_request(url="http://example/api", params={"q": "x"})

    assert result == {"ok": True}
    # Ensure both headers are preserved in return value
    assert headers == {"Link": "<https://api?page=2>; rel=\"next\"", "X-Total": "42"}


@pytest.mark.asyncio
async def test_make_request_with_refresh_and_text_round_064(monkeypatch):
    """
    - First response indicates expired token (401) so the code should call get_latest_token and re-request.
    - Second response is plain text; ensure the returned content is .text and headers reflect absence of Link/X-Total.
    """
    monkeypatch.setattr(base_mod, "httpx", FakeHTTPX)
    monkeypatch.setattr(base_mod, "httpx_verify_option", lambda: True)

    first = FakeResponse(status_code=401, headers={"Content-Type": "application/json"}, json_data={"expired": True})
    second = FakeResponse(status_code=200, headers={"Content-Type": "text/plain"}, json_data=None, text_data="plain-text-body")

    svc = TestService([first, second])
    svc.refresh = True

    result, headers = await svc._make_request(url="http://example/api", params=None)

    # Because second response has text/plain content-type path should return .text
    assert result == "plain-text-body"
    # No Link or X-Total present on second response
    assert headers == {}
    # Ensure refresh was invoked once
    assert svc._token_calls == 1


@pytest.mark.asyncio
async def test_make_request_raises_http_status_error_round_064(monkeypatch):
    """
    - Simulate a response whose raise_for_status raises an HTTPStatusError; the method should catch and
      re-raise the value returned by handle_http_status_error.
    """
    monkeypatch.setattr(base_mod, "httpx", FakeHTTPX)
    monkeypatch.setattr(base_mod, "httpx_verify_option", lambda: True)

    # response with status >= 400 triggers raise_for_status to raise FakeHTTPX.HTTPStatusError
    bad_resp = FakeResponse(status_code=500, headers={"Content-Type": "application/json"}, json_data={})

    svc = TestService([bad_resp])
    svc.refresh = False

    with pytest.raises(ValueError) as excinfo:
        await svc._make_request(url="http://example/api/error", params=None)
    assert "handled status error" in str(excinfo.value)


@pytest.mark.asyncio
async def test_make_request_raises_http_error_round_064(monkeypatch):
    """
    - Simulate execute_request raising an HTTPError (network-like failure); the method should catch and
      re-raise the value returned by handle_http_error.
    """
    # Patch the module-level httpx so the exception class used inside the module matches what we raise here
    monkeypatch.setattr(base_mod, "httpx", FakeHTTPX)
    monkeypatch.setattr(base_mod, "httpx_verify_option", lambda: True)

    # Configure the service so execute_request will raise a module-level HTTPError
    error_instance = base_mod.httpx.HTTPError("simulated network failure")
    svc = TestService([error_instance])
    svc.refresh = False

    with pytest.raises(KeyError) as excinfo:
        await svc._make_request(url="http://example/api/fail", params=None)
    assert "handled http error" in str(excinfo.value)
