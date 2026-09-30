import pytest
import httpx
from types import SimpleNamespace

from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime
from openhands.runtime.impl.action_execution.action_execution_client import ActionExecutionClient
from openhands.core.exceptions import AgentRuntimeDisconnectedError


def make_runtime(keep_runtime_alive: bool = True):
    """Create a RemoteRuntime instance without running its constructor.

    The returned object has the minimal attributes used by
    _send_action_server_request_impl: config.sandbox.keep_runtime_alive,
    runtime_id, log, and _resume_runtime.
    """
    rt = object.__new__(RemoteRuntime)
    rt.config = SimpleNamespace(sandbox=SimpleNamespace(keep_runtime_alive=keep_runtime_alive))
    rt.runtime_id = "runtime-123"
    rt._logs = []

    def log(level, message, exc_info=False):
        rt._logs.append((level, message, exc_info))

    rt.log = log

    # Default resume does nothing (success)
    def _resume_runtime_ok():
        rt._resumed = True

    rt._resume_runtime = _resume_runtime_ok

    return rt


def test_timeout_round_061(monkeypatch):
    rt = make_runtime()

    def _raise_timeout(self, method, url, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", _raise_timeout)

    with pytest.raises(httpx.TimeoutException):
        rt._send_action_server_request_impl("GET", "http://example")

    # confirm a log entry was recorded about timeout and it mentions the URL
    assert any(entry[0] == "error" and "http://example" in entry[1] for entry in rt._logs)


def test_http_404_raises_disconnected_round_061(monkeypatch):
    rt = make_runtime()

    e = httpx.HTTPError("not found")
    e.response = SimpleNamespace(status_code=404)

    def _raise_404(self, method, url, **kwargs):
        raise e

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", _raise_404)

    with pytest.raises(AgentRuntimeDisconnectedError) as excinfo:
        rt._send_action_server_request_impl("GET", "http://example")

    # The message should indicate the runtime is not responding and include the original error
    assert "Runtime is not responding" in str(excinfo.value)
    assert "not found" in str(excinfo.value)
    # check that the original exception is the __cause__
    assert excinfo.value.__cause__ is e


def test_http_502_raises_temporarily_unavailable_round_061(monkeypatch):
    rt = make_runtime()

    e = httpx.HTTPError("bad gateway")
    e.response = SimpleNamespace(status_code=502)

    def _raise_502(self, method, url, **kwargs):
        raise e

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", _raise_502)

    with pytest.raises(AgentRuntimeDisconnectedError) as excinfo:
        rt._send_action_server_request_impl("POST", "http://example/api")

    assert "temporarily unavailable" in str(excinfo.value)
    assert excinfo.value.__cause__ is e


def test_http_503_keep_alive_and_resume_success_round_061(monkeypatch):
    rt = make_runtime(keep_runtime_alive=True)

    calls = {"n": 0}

    e503 = httpx.HTTPError("service paused")
    e503.response = SimpleNamespace(status_code=503)

    def _first_503_then_ok(self, method, url, **kwargs):
        if calls["n"] == 0:
            calls["n"] += 1
            raise e503
        return "SENTINEL_RESPONSE"

    # make resume succeed (default behavior of make_runtime)
    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", _first_503_then_ok)

    result = rt._send_action_server_request_impl("GET", "http://example/act")

    assert result == "SENTINEL_RESPONSE"

    # logs should include that runtime appears paused and that resume succeeded
    info_messages = [m for (lvl, m, exc) in rt._logs if lvl == "info"]
    assert any("paused (503 response)" in m or "paused" in m for m in info_messages)
    assert any("Successfully resumed runtime" in m for m in info_messages)


def test_http_503_keep_alive_resume_fails_round_061(monkeypatch):
    rt = make_runtime(keep_runtime_alive=True)

    e503 = httpx.HTTPError("service paused")
    e503.response = SimpleNamespace(status_code=503)

    def _always_503(self, method, url, **kwargs):
        raise e503

    def _resume_raises():
        raise RuntimeError("resume failed")

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", _always_503)
    rt._resume_runtime = _resume_raises

    with pytest.raises(AgentRuntimeDisconnectedError) as excinfo:
        rt._send_action_server_request_impl("GET", "http://example/act")

    # The raised error should indicate runtime could not be resumed and be caused by the resume error
    assert "could not be resumed" in str(excinfo.value)
    cause = excinfo.value.__cause__
    assert isinstance(cause, RuntimeError)
    assert str(cause) == "resume failed"

    # ensure an error log was recorded for the failed resume with exc_info True
    assert any(lvl == "error" and exc for (lvl, msg, exc) in rt._logs)


def test_http_503_keep_alive_false_raises_disconnected_round_061(monkeypatch):
    rt = make_runtime(keep_runtime_alive=False)

    e503 = httpx.HTTPError("service paused")
    e503.response = SimpleNamespace(status_code=503)

    def _always_503(self, method, url, **kwargs):
        raise e503

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", _always_503)

    with pytest.raises(AgentRuntimeDisconnectedError) as excinfo:
        rt._send_action_server_request_impl("GET", "http://example/act")

    assert "temporarily unavailable" in str(excinfo.value)
    assert excinfo.value.__cause__ is e503

    # log should note keep_runtime_alive is False
    assert any("keep_runtime_alive is False" in msg for (lvl, msg, exc) in rt._logs if lvl == "info")


def test_other_http_error_re_raised_round_061(monkeypatch):
    rt = make_runtime()

    e500 = httpx.HTTPError("internal")
    e500.response = SimpleNamespace(status_code=500)

    def _raise_500(self, method, url, **kwargs):
        raise e500

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", _raise_500)

    with pytest.raises(httpx.HTTPError) as excinfo:
        rt._send_action_server_request_impl("GET", "http://example/act")

    # the original HTTPError should be re-raised (status_code preserved)
    assert hasattr(excinfo.value, "response")
    assert excinfo.value.response.status_code == 500
