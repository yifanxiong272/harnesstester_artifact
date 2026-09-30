import asyncio
import types
import pytest
import httpx
from types import SimpleNamespace
import builtins

from openhands.integrations.gitlab.service import base as base_module
from openhands.integrations.service_types import UnknownException

# A small fake AsyncClient to control post responses deterministically
class FakeResponse:
    def __init__(self, status_code=200, json_data=None, raise_exc=None):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc is not None:
            raise self._raise_exc

    def json(self):
        return self._json_data


class FakeAsyncClient:
    """Usage: set FakeAsyncClient.next_posts = [callable_or_response_or_exception, ...]
    Each item consumed in order when post(...) is awaited.
    If an item is a callable it will be called and the result used as the response.
    If it's an Exception instance the post will raise it.
    """

    next_posts = []

    def __init__(self, verify=True):
        self.verify = verify

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers=None, json=None):
        if not FakeAsyncClient.next_posts:
            raise RuntimeError("No configured fake responses")
        item = FakeAsyncClient.next_posts.pop(0)
        if isinstance(item, Exception):
            raise item
        if callable(item):
            return item()
        return item


@pytest.fixture(autouse=True)
def patch_httpx_and_verify(monkeypatch):
    # Patch the httpx.AsyncClient used in the module under test
    fake_httpx_ns = types.SimpleNamespace(
        AsyncClient=FakeAsyncClient,
        HTTPError=httpx.HTTPError,
        HTTPStatusError=httpx.HTTPStatusError,
    )
    monkeypatch.setattr(base_module, "httpx", fake_httpx_ns)
    # Patch verify option to be deterministic
    monkeypatch.setattr(base_module, "httpx_verify_option", lambda: True)
    yield


# Helper to bind the async method to a lightweight object with required attributes
def make_bound_executor(
    *, graphql_url="https://gitlab.example/graphql", headers=None, refresh=False
):
    obj = SimpleNamespace()
    obj.GRAPHQL_URL = graphql_url
    obj.refresh = refresh
    called = {"get_headers": 0, "get_latest_token": 0}

    async def _get_headers():
        called["get_headers"] += 1
        return dict(headers) if headers is not None else {"Authorization": "Bearer initial"}

    async def get_latest_token():
        called["get_latest_token"] += 1
        # pretend token rotation happened; subsequent _get_headers call can reflect it

    def _has_token_expired(status_code):
        # Helper for tests to set behavior via headers values
        # If status_code is 401 (unauthorized) treat expired
        return status_code == 401

    def handle_http_status_error(e):
        # Return an exception to be raised by the caller as the code under test does
        return RuntimeError("handled_status")

    def handle_http_error(e):
        return RuntimeError("handled_http")

    obj._get_headers = _get_headers
    obj.get_latest_token = get_latest_token
    obj._has_token_expired = _has_token_expired
    obj.handle_http_status_error = handle_http_status_error
    obj.handle_http_error = handle_http_error
    obj._called = called

    # Bind the async function defined on the class to this object instance
    bound = types.MethodType(base_module.GitLabMixinBase.execute_graphql_query, obj)
    return obj, bound


@pytest.mark.asyncio
async def test_successful_query_no_refresh_round_068():
    # variables None branch (lines ~100-102) -> should set to {}
    FakeAsyncClient.next_posts = [
        FakeResponse(status_code=200, json_data={"data": {"hello": "world"}})
    ]

    obj, bound = make_bound_executor(headers={"Authorization": "Bearer x"}, refresh=False)

    result = await bound("query { hello }")

    assert result == {"hello": "world"}
    # ensure _get_headers was called exactly once
    assert obj._called["get_headers"] == 1


@pytest.mark.asyncio
async def test_graphql_errors_raise_unknown_exception_round_068():
    # Response contains 'errors' key -> UnknownException should be raised (lines 129-135)
    FakeAsyncClient.next_posts = [
        FakeResponse(status_code=200, json_data={"errors": [{"message": "bad"}]})
    ]

    obj, bound = make_bound_executor()

    with pytest.raises(UnknownException) as excinfo:
        await bound("query { broken }")

    assert "GraphQL error: bad" in str(excinfo.value)


@pytest.mark.asyncio
async def test_token_refresh_and_retry_round_068():
    # First post returns 401 (expired token) so _has_token_expired True -> triggers refresh path
    first = FakeResponse(status_code=401, json_data={"data": None})
    # After refresh, second returns success
    second = FakeResponse(status_code=200, json_data={"data": {"refreshed": True}})

    FakeAsyncClient.next_posts = [first, second]

    obj, bound = make_bound_executor(refresh=True)

    # Override _get_headers to show token change when called second time
    async def _get_headers_variant():
        # Emulate that get_latest_token updated a token between calls by toggling counter
        count = obj._called.get("get_headers", 0)
        obj._called["get_headers"] = count + 1
        if count == 0:
            return {"Authorization": "Bearer old"}
        return {"Authorization": "Bearer new"}

    async def get_latest_token():
        obj._called["get_latest_token"] = obj._called.get("get_latest_token", 0) + 1

    obj._get_headers = _get_headers_variant
    obj.get_latest_token = get_latest_token

    result = await bound("query { refresh }")

    assert result == {"refreshed": True}
    # _get_headers called at least twice (before and after refresh)
    assert obj._called["get_headers"] >= 2
    assert obj._called.get("get_latest_token", 0) == 1


@pytest.mark.asyncio
async def test_http_exceptions_handling_round_068():
    # Test both HTTPStatusError and HTTPError handled via instance methods (lines 136-139)

    # First scenario: post returns a response whose raise_for_status raises HTTPStatusError
    status_exc = httpx.HTTPStatusError("status", request=None, response=None)
    resp_raises = FakeResponse(status_code=500, json_data={"data": None}, raise_exc=status_exc)

    FakeAsyncClient.next_posts = [resp_raises]

    # Use an object whose handle_http_status_error returns a specific exception
    obj = SimpleNamespace()
    obj.GRAPHQL_URL = "u"
    obj.refresh = False

    async def _get_headers():
        return {"Authorization": "Bearer x"}

    async def bound_call(e):
        # helper to satisfy binding signature
        pass

    async def get_latest_token():
        return None

    def _has_token_expired(status_code):
        return False

    def handle_http_status_error(e):
        return ValueError("status handled")

    def handle_http_error(e):
        return ValueError("http handled")

    obj._get_headers = _get_headers
    obj.get_latest_token = get_latest_token
    obj._has_token_expired = _has_token_expired
    obj.handle_http_status_error = handle_http_status_error
    obj.handle_http_error = handle_http_error

    bound = types.MethodType(base_module.GitLabMixinBase.execute_graphql_query, obj)

    with pytest.raises(ValueError) as excinfo1:
        await bound("query { status_err }")
    assert "status handled" in str(excinfo1.value)

    # Second scenario: post itself raises an HTTPError
    FakeAsyncClient.next_posts = [httpx.HTTPError("conn error")]

    with pytest.raises(ValueError) as excinfo2:
        await bound("query { conn_err }")
    assert "http handled" in str(excinfo2.value)
