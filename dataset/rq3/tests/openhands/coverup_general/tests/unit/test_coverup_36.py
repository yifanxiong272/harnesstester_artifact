# file: openhands/runtime/impl/remote/remote_runtime.py:556-610
# asked: {"lines": [559, 560, 561, 562, 563, 564, 566, 568, 569, 570, 571, 572, 573, 575, 576, 577, 578, 579, 580, 581, 582, 584, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 603, 604, 606, 607, 608, 610], "branches": [[569, 570], [569, 578], [570, 571], [570, 575], [578, 579], [578, 610], [579, 580], [579, 602]]}
# gained: {"lines": [559, 560, 561, 562, 563, 564, 566, 568, 569, 570, 571, 572, 573, 575, 576, 577, 578, 579, 580, 581, 582, 584, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 603, 604, 606, 607, 608, 610], "branches": [[569, 570], [569, 578], [570, 571], [570, 575], [578, 579], [578, 610], [579, 580], [579, 602]]}

import pytest
from types import SimpleNamespace
import httpx

from openhands.core.exceptions import AgentRuntimeDisconnectedError
from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime
from openhands.runtime.impl.action_execution.action_execution_client import ActionExecutionClient


def make_remote_runtime(keep_runtime_alive: bool = True):
    # Create instance without calling __init__
    remote = object.__new__(RemoteRuntime)
    # minimal attributes used by _send_action_server_request_impl
    remote.config = SimpleNamespace(sandbox=SimpleNamespace(keep_runtime_alive=keep_runtime_alive))
    remote.runtime_id = "runtime-123"
    # simple log collector
    remote._logs = []

    def log(level, message, exc_info=None):
        remote._logs.append((level, message, exc_info))

    remote.log = log
    return remote


def set_parent_side_effects(monkeypatch, side_effects):
    """
    Monkeypatch ActionExecutionClient._send_action_server_request to pop from side_effects.
    Each item in side_effects can be:
      - an Exception instance -> function will raise it
      - a return value -> function will return it
    """
    effects = list(side_effects)

    def fake_send(self, method, url, **kwargs):
        if not effects:
            raise RuntimeError("No more side effects configured")
        next_item = effects.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", fake_send)


def test_timeout_exception_re_raises_and_logs(monkeypatch):
    remote = make_remote_runtime()
    # parent raises TimeoutException
    set_parent_side_effects(monkeypatch, [httpx.TimeoutException("timed out")])
    with pytest.raises(httpx.TimeoutException):
        remote._send_action_server_request_impl("GET", "http://example.com")
    # ensure log captured the timeout error message including the url
    assert remote._logs, "log should have been called"
    level, message, exc_info = remote._logs[-1]
    assert level == "error"
    assert "http://example.com" in message


@pytest.mark.parametrize("status,expected_msg_part", [
    (404, "Runtime is not responding"),
    (502, "temporarily unavailable"),
    (504, "temporarily unavailable"),
])
def test_http_error_404_502_504_raise_agent_disconnected(monkeypatch, status, expected_msg_part):
    remote = make_remote_runtime()
    # create HTTPError with response.status_code
    err = httpx.HTTPError(f"error {status}")
    err.response = SimpleNamespace(status_code=status)
    set_parent_side_effects(monkeypatch, [err])
    with pytest.raises(AgentRuntimeDisconnectedError) as ei:
        remote._send_action_server_request_impl("POST", "http://example.com/action")
    # assert message contains expected text and original error text
    assert expected_msg_part in str(ei.value)
    assert "error" in str(ei.value)


def test_http_error_503_keep_alive_resume_success(monkeypatch):
    remote = make_remote_runtime(keep_runtime_alive=True)
    # initial HTTPError 503, then on retry return a successful httpx.Response
    http_err = httpx.HTTPError("service paused")
    http_err.response = SimpleNamespace(status_code=503)
    success_response = httpx.Response(200)
    set_parent_side_effects(monkeypatch, [http_err, success_response])

    # patch _resume_runtime to record it was called
    called = {"resume": False}

    def fake_resume():
        called["resume"] = True

    remote._resume_runtime = fake_resume

    resp = remote._send_action_server_request_impl("GET", "http://example.com/resume")
    assert called["resume"] is True
    assert isinstance(resp, httpx.Response)
    assert resp.status_code == 200
    # logs should include resume success info message
    assert any("Successfully resumed runtime" in m for _, m, _ in remote._logs)


def test_http_error_503_keep_alive_resume_fails(monkeypatch):
    remote = make_remote_runtime(keep_runtime_alive=True)
    http_err = httpx.HTTPError("service paused")
    http_err.response = SimpleNamespace(status_code=503)
    set_parent_side_effects(monkeypatch, [http_err])
    # _resume_runtime raises an exception
    def fake_resume():
        raise RuntimeError("resume failed")

    remote._resume_runtime = fake_resume

    with pytest.raises(AgentRuntimeDisconnectedError) as ei:
        remote._send_action_server_request_impl("GET", "http://example.com/resumefail")
    # message should indicate resume failure and include original error text
    assert "could not be resumed" in str(ei.value) or "could not be resumed" in repr(ei.value)
    assert "service paused" in str(ei.value) or "resume failed" in str(ei.value)


def test_http_error_503_keep_alive_false_raises(monkeypatch):
    remote = make_remote_runtime(keep_runtime_alive=False)
    http_err = httpx.HTTPError("service paused")
    http_err.response = SimpleNamespace(status_code=503)
    set_parent_side_effects(monkeypatch, [http_err])
    with pytest.raises(AgentRuntimeDisconnectedError) as ei:
        remote._send_action_server_request_impl("GET", "http://example.com/paused")
    assert "temporarily unavailable" in str(ei.value)


def test_other_http_error_is_reraised(monkeypatch):
    remote = make_remote_runtime()
    http_err = httpx.HTTPError("auth required")
    http_err.response = SimpleNamespace(status_code=401)
    set_parent_side_effects(monkeypatch, [http_err])
    with pytest.raises(httpx.HTTPError) as ei:
        remote._send_action_server_request_impl("GET", "http://example.com/other")
    # ensure the raised error message matches original
    assert "auth required" in str(ei.value)
