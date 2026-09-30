import types
import httpx
import pytest
from types import SimpleNamespace

import openhands.runtime.impl.remote.remote_runtime as remote_runtime_mod
from openhands.core.exceptions import AgentRuntimeDisconnectedError

RemoteRuntime = remote_runtime_mod.RemoteRuntime
ActionExecutionClient = remote_runtime_mod.ActionExecutionClient


def make_runtime(keep_alive=True):
    """Create a minimal RemoteRuntime-like object for testing the target method.

    We create an instance without running __init__ and attach only the
    attributes/methods that _send_action_server_request_impl uses.
    """
    rt = object.__new__(RemoteRuntime)
    rt.config = SimpleNamespace(sandbox=SimpleNamespace(keep_runtime_alive=keep_alive))
    rt.runtime_id = "test-runtime"
    rt.logged = []

    def log(level, message, exc_info=False):
        # Keep logs deterministic and inspectable
        rt.logged.append((level, message, bool(exc_info)))

    rt.log = log

    # Default _resume_runtime does nothing (can be replaced per-test)
    def _resume_runtime():
        rt._resumed = True

    rt._resume_runtime = _resume_runtime
    return rt


def test_timeout_round_061(monkeypatch):
    rt = make_runtime()

    # Make the parent class method raise a TimeoutException
    def raise_timeout(self, method, url, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", raise_timeout)

    with pytest.raises(httpx.TimeoutException):
        RemoteRuntime._send_action_server_request_impl(rt, "GET", "http://example")

    # Ensure the timeout was logged
    assert any(
        "No response received within the timeout period" in msg for (_lvl, msg, _exc) in rt.logged
    )


def test_http_404_round_061(monkeypatch):
    rt = make_runtime()

    # Prepare HTTPError with .response.status_code = 404
    def raise_http_404(self, method, url, **kwargs):
        e = httpx.HTTPError("not found")
        e.response = SimpleNamespace(status_code=404)
        raise e

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", raise_http_404)

    with pytest.raises(AgentRuntimeDisconnectedError) as excinfo:
        RemoteRuntime._send_action_server_request_impl(rt, "GET", "http://example")

    # Message should indicate runtime not responding (404 branch)
    assert "Runtime is not responding" in str(excinfo.value)


def test_http_502_round_061(monkeypatch):
    rt = make_runtime()

    # Prepare HTTPError with .response.status_code = 502
    def raise_http_502(self, method, url, **kwargs):
        e = httpx.HTTPError("bad gateway")
        e.response = SimpleNamespace(status_code=502)
        raise e

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", raise_http_502)

    with pytest.raises(AgentRuntimeDisconnectedError) as excinfo:
        RemoteRuntime._send_action_server_request_impl(rt, "POST", "http://example/api")

    # Message should indicate temporarily unavailable (502/504 branch)
    assert "temporarily unavailable" in str(excinfo.value)


def test_http_503_resume_success_round_061(monkeypatch):
    rt = make_runtime(keep_alive=True)

    # We want the first call to raise 503, then after _resume_runtime the second call returns a Response
    call_state = {"count": 0}

    response_obj = httpx.Response(200, content=b"ok")

    def parent_behaviour(self, method, url, **kwargs):
        if call_state["count"] == 0:
            call_state["count"] += 1
            e = httpx.HTTPError("service paused")
            e.response = SimpleNamespace(status_code=503)
            raise e
        else:
            return response_obj

    # Make _resume_runtime set a flag and not raise
    def resume_success():
        rt._resumed_called = True

    rt._resume_runtime = resume_success

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", parent_behaviour)

    res = RemoteRuntime._send_action_server_request_impl(rt, "GET", "http://example/act")

    assert res is response_obj
    assert getattr(rt, "_resumed_called", False) is True
    # Ensure logs include successful resume message
    assert any("Successfully resumed runtime after 503" in msg for (_lvl, msg, _exc) in rt.logged)


def test_http_503_resume_fail_round_061(monkeypatch):
    rt = make_runtime(keep_alive=True)

    # Parent raises 503 once
    def parent_behaviour(self, method, url, **kwargs):
        e = httpx.HTTPError("service paused")
        e.response = SimpleNamespace(status_code=503)
        raise e

    # Make _resume_runtime raise an error
    def resume_fail():
        raise RuntimeError("resume failed")

    rt._resume_runtime = resume_fail
    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", parent_behaviour)

    with pytest.raises(AgentRuntimeDisconnectedError) as excinfo:
        RemoteRuntime._send_action_server_request_impl(rt, "GET", "http://example/act")

    # The raised message should mention that runtime could not be resumed
    assert "could not be resumed" in str(excinfo.value)
    # And we should have logged a failure about resume
    assert any("Failed to resume runtime after 503" in msg for (_lvl, msg, _exc) in rt.logged)


def test_http_500_reraise_round_061(monkeypatch):
    rt = make_runtime()

    # HTTPError with status_code not in handled list should be re-raised
    def raise_http_500(self, method, url, **kwargs):
        e = httpx.HTTPError("server error")
        e.response = SimpleNamespace(status_code=500)
        raise e

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", raise_http_500)

    with pytest.raises(httpx.HTTPError):
        RemoteRuntime._send_action_server_request_impl(rt, "GET", "http://example")
