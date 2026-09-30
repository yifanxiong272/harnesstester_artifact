# file: openhands/runtime/impl/remote/remote_runtime.py:556-610
# asked: {"lines": [559, 560, 561, 562, 563, 564, 566, 568, 569, 570, 571, 572, 573, 575, 576, 577, 578, 579, 580, 581, 582, 584, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 603, 604, 606, 607, 608, 610], "branches": [[569, 570], [569, 578], [570, 571], [570, 575], [578, 579], [578, 610], [579, 580], [579, 602]]}
# gained: {"lines": [559, 560, 561, 562, 563, 564, 566, 568, 569, 570, 571, 572, 573, 575, 576, 577, 578, 579, 580, 581, 582, 584, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 603, 604, 606, 607, 608, 610], "branches": [[569, 570], [569, 578], [570, 571], [570, 575], [578, 579], [578, 610], [579, 580], [579, 602]]}

import pytest
import httpx
from types import SimpleNamespace

from openhands.core.exceptions import AgentRuntimeDisconnectedError
from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime
from openhands.runtime.impl.action_execution.action_execution_client import (
    ActionExecutionClient,
)


def make_runtime():
    # Create instance without calling __init__
    rt = object.__new__(RemoteRuntime)
    # minimal attributes used by _send_action_server_request_impl
    rt.runtime_id = "runtime-123"
    rt._logged = []
    def log(level, msg, exc_info=False):
        rt._logged.append((level, msg, exc_info))
    rt.log = log
    rt._resume_called = False
    def resume_ok():
        rt._resume_called = True
    rt._resume_runtime = resume_ok
    return rt


def test_timeout_exception_logs_and_raises(monkeypatch):
    rt = make_runtime()

    def fake_send(self, method, url, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", fake_send)

    with pytest.raises(httpx.TimeoutException):
        rt._send_action_server_request_impl("GET", "https://example.test/timeout")

    # ensure a log entry was made with error and contains the url
    assert rt._logged, "Expected at least one log entry"
    level, msg, exc_info = rt._logged[-1]
    assert level == "error"
    assert "https://example.test/timeout" in msg


def _make_http_status_error(status_code):
    req = httpx.Request("GET", "https://example.test/")
    resp = httpx.Response(status_code)
    return httpx.HTTPStatusError(f"status {status_code}", request=req, response=resp)


@pytest.mark.parametrize("status_code, expected_substr", [
    (404, "Runtime is not responding"),
    (502, "temporarily unavailable"),
    (504, "temporarily unavailable"),
])
def test_http_404_502_504_raise_agent_disconnected(monkeypatch, status_code, expected_substr):
    rt = make_runtime()

    def fake_send(self, method, url, **kwargs):
        raise _make_http_status_error(status_code)

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", fake_send)

    with pytest.raises(AgentRuntimeDisconnectedError) as excinfo:
        rt._send_action_server_request_impl("POST", "https://example.test/err")

    assert expected_substr in str(excinfo.value)


def test_http_503_keep_alive_true_resume_success(monkeypatch):
    rt = make_runtime()
    # enable keep alive
    rt.config = SimpleNamespace(sandbox=SimpleNamespace(keep_runtime_alive=True))

    # create a call-counter fake: first call raises 503, second returns success
    state = {"calls": 0}
    good_response = httpx.Response(200)

    def fake_send(self, method, url, **kwargs):
        state["calls"] += 1
        if state["calls"] == 1:
            raise _make_http_status_error(503)
        return good_response

    # replace resume to set flag (already default sets _resume_called True)
    def resume_and_mark():
        rt._resume_called = True

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", fake_send)
    rt._resume_runtime = resume_and_mark

    resp = rt._send_action_server_request_impl("GET", "https://example.test/503")
    assert resp is good_response
    assert rt._resume_called is True

    # verify that logs include info about pause and success
    msgs = [m for (_, m, _) in rt._logged]
    assert any("Runtime appears to be paused" in m for m in msgs)
    assert any("Successfully resumed runtime" in m for m in msgs)


def test_http_503_keep_alive_true_resume_failure(monkeypatch):
    rt = make_runtime()
    rt.config = SimpleNamespace(sandbox=SimpleNamespace(keep_runtime_alive=True))

    def fake_send(self, method, url, **kwargs):
        raise _make_http_status_error(503)

    def resume_fails():
        raise RuntimeError("resume failed")

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", fake_send)
    rt._resume_runtime = resume_fails

    with pytest.raises(AgentRuntimeDisconnectedError) as excinfo:
        rt._send_action_server_request_impl("GET", "https://example.test/503fail")

    # ensure the raised error mentions that runtime is paused and could not be resumed
    assert "could not be resumed" in str(excinfo.value)
    # ensure an error log about failing to resume was created (exc_info True)
    assert any(level == "error" and exc for (level, _, exc) in rt._logged), rt._logged


def test_http_503_keep_alive_false_raises_agent_disconnected(monkeypatch):
    rt = make_runtime()
    rt.config = SimpleNamespace(sandbox=SimpleNamespace(keep_runtime_alive=False))

    def fake_send(self, method, url, **kwargs):
        raise _make_http_status_error(503)

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", fake_send)

    with pytest.raises(AgentRuntimeDisconnectedError) as excinfo:
        rt._send_action_server_request_impl("GET", "https://example.test/503nope")

    assert "temporarily unavailable" in str(excinfo.value).lower()
    # check that an info log about keep_runtime_alive False was emitted
    assert any("but keep_runtime_alive is False" in msg for (_, msg, _) in rt._logged)


def test_other_http_error_is_reraised(monkeypatch):
    rt = make_runtime()

    def fake_send(self, method, url, **kwargs):
        # plain HTTPError without response attribute
        raise httpx.HTTPError("generic http error")

    monkeypatch.setattr(ActionExecutionClient, "_send_action_server_request", fake_send)

    with pytest.raises(httpx.HTTPError):
        rt._send_action_server_request_impl("GET", "https://example.test/other")
