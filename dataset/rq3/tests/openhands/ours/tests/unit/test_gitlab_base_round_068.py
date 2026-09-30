import types
import pytest
import httpx

import openhands.integrations.gitlab.service.base as base

# Provide a tiny concrete subclass implementing required abstract methods so we can instantiate without TypeError
class ConcreteGitLab(base.GitLabMixinBase):
    # Implement abstract methods with permissive signatures
    def _get_cursorrules_url(self, *args, **kwargs):
        return ""

    def _get_file_name_from_item(self, *args, **kwargs):
        return "file"

    def _get_file_path_from_item(self, *args, **kwargs):
        return "path"

    def _get_microagents_directory_params(self, *args, **kwargs):
        return {}

    def _get_microagents_directory_url(self, *args, **kwargs):
        return ""

    def _is_valid_microagent_file(self, *args, **kwargs):
        return True


# All test function names must end with _round_068

@pytest.mark.asyncio
async def test_execute_graphql_query_returns_data_round_068(monkeypatch):
    """Normal flow: variables is None, no token refresh, returns data."""
    # Prepare instance without running any __init__ by using object.__new__ on the concrete subclass
    inst = object.__new__(ConcreteGitLab)
    inst.GRAPHQL_URL = "http://example/graphql"
    inst.refresh = False
    inst._token = "initial"

    async def _get_headers(self):
        return {"Authorization": f"Bearer {self._token}"}

    async def get_latest_token(self):
        # should not be called in this test
        self._token = "new"

    def _has_token_expired(self, status_code):
        return False

    def handle_http_status_error(self, e):
        return e

    def handle_http_error(self, e):
        return e

    # Bind methods
    inst._get_headers = types.MethodType(_get_headers, inst)
    inst.get_latest_token = types.MethodType(get_latest_token, inst)
    inst._has_token_expired = types.MethodType(_has_token_expired, inst)
    inst.handle_http_status_error = types.MethodType(handle_http_status_error, inst)
    inst.handle_http_error = types.MethodType(handle_http_error, inst)

    # Fake AsyncClient that returns a successful response
    class FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class FakeAsyncClient:
        def __init__(self, verify=None):
            self.calls = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            self.calls.append((url, headers, json))
            return FakeResponse(200, {"data": {"foo": "bar"}})

    # Patch AsyncClient and verify option
    monkeypatch.setattr(base.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(base, "httpx_verify_option", lambda: True)

    result = await base.GitLabMixinBase.execute_graphql_query(inst, "{dummy}", None)
    assert result == {"foo": "bar"}


@pytest.mark.asyncio
async def test_execute_graphql_query_token_refresh_round_068(monkeypatch):
    """When refresh is True and token expired on first attempt, get_latest_token is called and second post used."""
    inst = object.__new__(ConcreteGitLab)
    inst.GRAPHQL_URL = "http://example/graphql"
    inst.refresh = True
    inst._token = "old-token"
    inst.latest_token_called = False

    async def _get_headers(self):
        return {"Authorization": f"Bearer {self._token}"}

    async def get_latest_token(self):
        # Simulate obtaining a new token
        self.latest_token_called = True
        self._token = "new-token"

    def _has_token_expired(self, status_code):
        # treat 401 as expired
        return status_code == 401

    def handle_http_status_error(self, e):
        return e

    def handle_http_error(self, e):
        return e

    inst._get_headers = types.MethodType(_get_headers, inst)
    inst.get_latest_token = types.MethodType(get_latest_token, inst)
    inst._has_token_expired = types.MethodType(_has_token_expired, inst)
    inst.handle_http_status_error = types.MethodType(handle_http_status_error, inst)
    inst.handle_http_error = types.MethodType(handle_http_error, inst)

    class FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class FakeAsyncClient:
        def __init__(self, verify=None):
            self.calls = []
            # sequence: first call returns 401, second returns 200
            self._seq = [FakeResponse(401, {"data": None}), FakeResponse(200, {"data": {"ok": True}})]

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            self.calls.append((url, headers, json))
            return self._seq.pop(0)

    monkeypatch.setattr(base.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(base, "httpx_verify_option", lambda: True)

    result = await base.GitLabMixinBase.execute_graphql_query(inst, "{dummy}", {})
    # After refresh flow, get_latest_token must have been called and result from second response returned
    assert inst.latest_token_called is True
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_execute_graphql_query_graphql_error_raises_unknown_round_068(monkeypatch):
    """If GraphQL 'errors' key is present in response.json, UnknownException is raised."""
    inst = object.__new__(ConcreteGitLab)
    inst.GRAPHQL_URL = "http://example/graphql"
    inst.refresh = False

    async def _get_headers(self):
        return {"Authorization": "Bearer x"}

    def _has_token_expired(self, status_code):
        return False

    async def get_latest_token(self):
        return None

    def handle_http_status_error(self, e):
        return e

    def handle_http_error(self, e):
        return e

    inst._get_headers = types.MethodType(_get_headers, inst)
    inst._has_token_expired = types.MethodType(_has_token_expired, inst)
    inst.get_latest_token = types.MethodType(get_latest_token, inst)
    inst.handle_http_status_error = types.MethodType(handle_http_status_error, inst)
    inst.handle_http_error = types.MethodType(handle_http_error, inst)

    class FakeResponse:
        def __init__(self):
            self.status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"errors": [{"message": "boom"}]}

    class FakeAsyncClient:
        def __init__(self, verify=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            return FakeResponse()

    monkeypatch.setattr(base.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(base, "httpx_verify_option", lambda: True)

    with pytest.raises(base.UnknownException) as excinfo:
        await base.GitLabMixinBase.execute_graphql_query(inst, "{q}", None)
    assert "GraphQL error" in str(excinfo.value)


@pytest.mark.asyncio
async def test_execute_graphql_query_http_status_error_handled_round_068(monkeypatch):
    """If response.raise_for_status raises httpx.HTTPStatusError, the service's handler is invoked and its returned exception is raised."""
    inst = object.__new__(ConcreteGitLab)
    inst.GRAPHQL_URL = "http://example/graphql"
    inst.refresh = False

    async def _get_headers(self):
        return {"Authorization": "Bearer x"}

    def _has_token_expired(self, status_code):
        return False

    async def get_latest_token(self):
        return None

    # make handlers return specific exceptions to be raised by the 'raise self.handle...' pattern
    def handle_http_status_error(self, e):
        return ValueError("handled status")

    def handle_http_error(self, e):
        return RuntimeError("handled http")

    inst._get_headers = types.MethodType(_get_headers, inst)
    inst._has_token_expired = types.MethodType(_has_token_expired, inst)
    inst.get_latest_token = types.MethodType(get_latest_token, inst)
    inst.handle_http_status_error = types.MethodType(handle_http_status_error, inst)
    inst.handle_http_error = types.MethodType(handle_http_error, inst)

    class FakeResponse:
        def __init__(self):
            self.status_code = 500

        def raise_for_status(self):
            # construct an httpx.HTTPStatusError; providing request/response None is accepted
            raise httpx.HTTPStatusError("boom", request=None, response=None)

        def json(self):
            return {}

    class FakeAsyncClient:
        def __init__(self, verify=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            return FakeResponse()

    monkeypatch.setattr(base.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(base, "httpx_verify_option", lambda: True)

    with pytest.raises(ValueError) as excinfo:
        await base.GitLabMixinBase.execute_graphql_query(inst, "{q}", None)
    assert "handled status" in str(excinfo.value)


@pytest.mark.asyncio
async def test_execute_graphql_query_http_error_handled_round_068(monkeypatch):
    """If client.post raises httpx.HTTPError, the service's HTTP error handler result is raised."""
    inst = object.__new__(ConcreteGitLab)
    inst.GRAPHQL_URL = "http://example/graphql"
    inst.refresh = False

    async def _get_headers(self):
        return {"Authorization": "Bearer x"}

    def _has_token_expired(self, status_code):
        return False

    async def get_latest_token(self):
        return None

    def handle_http_status_error(self, e):
        return e

    def handle_http_error(self, e):
        return RuntimeError("handled http")

    inst._get_headers = types.MethodType(_get_headers, inst)
    inst._has_token_expired = types.MethodType(_has_token_expired, inst)
    inst.get_latest_token = types.MethodType(get_latest_token, inst)
    inst.handle_http_status_error = types.MethodType(handle_http_status_error, inst)
    inst.handle_http_error = types.MethodType(handle_http_error, inst)

    class FakeAsyncClient:
        def __init__(self, verify=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            # simulate a transport error
            raise httpx.HTTPError("network fail")

    monkeypatch.setattr(base.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(base, "httpx_verify_option", lambda: True)

    with pytest.raises(RuntimeError) as excinfo:
        await base.GitLabMixinBase.execute_graphql_query(inst, "{q}", None)
    assert "handled http" in str(excinfo.value)
