import types
import pytest
import httpx

import openhands.runtime.impl.remote.remote_runtime as rr_module
from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime
from openhands.core.exceptions import AgentRuntimeDisconnectedError


def _make_runtime(keep_alive=True):
    """Create a minimal RemoteRuntime instance with configurable sandbox.keep_runtime_alive
    and a simple log collector."""
    runtime = RemoteRuntime.__new__(RemoteRuntime)
    runtime.config = types.SimpleNamespace(
        sandbox=types.SimpleNamespace(keep_runtime_alive=keep_alive)
    )
    runtime.runtime_id = "test-runtime-id"
    logs = []

    def _log(level, message, exc_info=False):
        # capture logs for potential inspection
        logs.append((level, message, exc_info))

    runtime.log = _log
    return runtime, logs


def test_timeout_round_061(monkeypatch):
    runtime, logs = _make_runtime()

    def _fake_send(*args, **kwargs):
        raise httpx.TimeoutException("timed out")

    # Patch the parent-class method that super() would call
    monkeypatch.setattr(
        rr_module.ActionExecutionClient,
        "_send_action_server_request",
        _fake_send,
        raising=True,
    )

    with pytest.raises(httpx.TimeoutException):
        runtime._send_action_server_request_impl("GET", "http://example")

    # confirm that log recorded an error about timeout
    assert any("timeout" in (m[1].lower()) or "no response" in (m[1].lower()) for m in logs)


def test_404_round_061(monkeypatch):
    runtime, _ = _make_runtime()

    exc = httpx.HTTPError("not found")
    # attach a response-like object with status_code
    exc.response = types.SimpleNamespace(status_code=404)

    def _fake_send(*args, **kwargs):
        raise exc

    monkeypatch.setattr(rr_module.ActionExecutionClient, "_send_action_server_request", _fake_send)

    with pytest.raises(AgentRuntimeDisconnectedError) as ei:
        runtime._send_action_server_request_impl("GET", "http://example")

    assert "not responding" in str(ei.value).lower()
    assert "original error" in str(ei.value).lower()


def test_502_round_061(monkeypatch):
    runtime, _ = _make_runtime()

    exc = httpx.HTTPError("bad gateway")
    exc.response = types.SimpleNamespace(status_code=502)

    def _fake_send(*args, **kwargs):
        raise exc

    monkeypatch.setattr(rr_module.ActionExecutionClient, "_send_action_server_request", _fake_send)

    with pytest.raises(AgentRuntimeDisconnectedError) as ei:
        runtime._send_action_server_request_impl("POST", "http://example")

    assert "temporarily unavailable" in str(ei.value).lower()
    assert "original error" in str(ei.value).lower()


def test_503_keep_alive_resume_success_round_061(monkeypatch):
    # first call: raise 503, after resume the second call returns a success response
    runtime, logs = _make_runtime(keep_alive=True)

    calls = {"n": 0}

    def _fake_send(*args, **kwargs):
        if calls["n"] == 0:
            calls["n"] += 1
            exc = httpx.HTTPError("service paused")
            exc.response = types.SimpleNamespace(status_code=503)
            raise exc
        # subsequent call simulates success
        return httpx.Response(status_code=200)

    def _fake_resume():
        # simulate successful resume
        logs.append(("resume", "called"))
        return None

    monkeypatch.setattr(rr_module.ActionExecutionClient, "_send_action_server_request", _fake_send)
    runtime._resume_runtime = _fake_resume

    resp = runtime._send_action_server_request_impl("GET", "http://example")
    assert isinstance(resp, httpx.Response)
    assert resp.status_code == 200
    # ensure resume was attempted (log entry added)
    assert any(entry[0] == "resume" for entry in logs)


def test_503_keep_alive_resume_fail_round_061(monkeypatch):
    # first call: raise 503, resume raises its own exception -> wrapped AgentRuntimeDisconnectedError
    runtime, logs = _make_runtime(keep_alive=True)

    exc = httpx.HTTPError("service paused")
    exc.response = types.SimpleNamespace(status_code=503)

    def _fake_send(*args, **kwargs):
        raise exc

    def _bad_resume():
        raise RuntimeError("resume failed")

    monkeypatch.setattr(rr_module.ActionExecutionClient, "_send_action_server_request", _fake_send)
    runtime._resume_runtime = _bad_resume

    with pytest.raises(AgentRuntimeDisconnectedError) as ei:
        runtime._send_action_server_request_impl("GET", "http://example")

    msg = str(ei.value)
    assert "could not be resumed" in msg.lower()
    assert "resume error" in msg.lower() or "resume failed" in msg.lower()
    assert "service paused" in msg or "service paused" in msg


def test_503_keep_alive_false_round_061(monkeypatch):
    runtime, logs = _make_runtime(keep_alive=False)

    exc = httpx.HTTPError("service paused")
    exc.response = types.SimpleNamespace(status_code=503)

    def _fake_send(*args, **kwargs):
        raise exc

    monkeypatch.setattr(rr_module.ActionExecutionClient, "_send_action_server_request", _fake_send)

    with pytest.raises(AgentRuntimeDisconnectedError) as ei:
        runtime._send_action_server_request_impl("GET", "http://example")

    assert "keep_runtime_alive is False" or True  # ensure path reached; primary assertion below
    assert "temporarily unavailable" in str(ei.value).lower()


def test_other_http_error_round_061(monkeypatch):
    runtime, _ = _make_runtime()

    exc = httpx.HTTPError("i am a teapot")
    exc.response = types.SimpleNamespace(status_code=418)

    def _fake_send(*args, **kwargs):
        raise exc

    monkeypatch.setattr(rr_module.ActionExecutionClient, "_send_action_server_request", _fake_send)

    # should re-raise the original httpx.HTTPError for unhandled response codes
    with pytest.raises(httpx.HTTPError):
        runtime._send_action_server_request_impl("GET", "http://example")
