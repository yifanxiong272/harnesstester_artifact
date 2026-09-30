# file: openhands/runtime/impl/remote/remote_runtime.py:423-490
# asked: {"lines": [424, 425, 426, 427, 429, 430, 431, 433, 434, 435, 436, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 453, 454, 455, 456, 457, 458, 459, 461, 462, 464, 466, 467, 468, 470, 471, 473, 474, 475, 476, 479, 480, 484, 486, 487, 488, 490], "branches": [[444, 445], [444, 453], [453, 454], [453, 465], [465, 470], [465, 473], [473, 474], [473, 484], [474, 475], [474, 479]]}
# gained: {"lines": [424, 425, 426, 427, 429, 430, 431, 433, 434, 435, 436, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 453, 454, 455, 456, 457, 458, 459, 461, 462, 464, 466, 467, 468, 470, 471, 473, 474, 475, 476, 479, 480, 484, 486, 487, 488, 490], "branches": [[444, 445], [444, 453], [453, 454], [453, 465], [465, 470], [465, 473], [473, 474], [473, 484], [474, 475], [474, 479]]}

import httpx
import pytest
from types import SimpleNamespace

from openhands.core.exceptions import AgentRuntimeNotReadyError, AgentRuntimeUnavailableError
from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime


def make_runtime(runtime_id="r1", api_url="http://api"):
    # Create an instance without calling __init__
    rt = object.__new__(RemoteRuntime)
    # minimal attributes used by _wait_until_alive_impl
    rt.runtime_url = "http://runtime"
    rt.runtime_id = runtime_id
    rt.config = SimpleNamespace(sandbox=SimpleNamespace(remote_runtime_api_url=api_url))
    # capture logs
    rt._logs = []

    def log(level, message, exc_info=None):
        rt._logs.append((level, message))
    rt.log = log

    return rt


def make_response(json_obj):
    return SimpleNamespace(json=lambda: json_obj)


def test_ready_check_alive_success():
    rt = make_runtime(runtime_id="rid-success")
    # runtime_data indicates ready
    runtime_data = {"runtime_id": "rid-success", "pod_status": "Ready"}
    rt._send_runtime_api_request = lambda method, url, **kwargs: make_response(runtime_data)

    # check_if_alive should be called and succeed (no exception)
    called = {"alive": False}

    def check_if_alive():
        called["alive"] = True
    rt.check_if_alive = check_if_alive

    # Should not raise
    rt._wait_until_alive_impl()

    # check_if_alive called and appropriate logs present
    assert called["alive"] is True
    # ensure some debug logs exist about waiting and received response
    assert any("Waiting for runtime" in m for _, m in rt._logs)
    assert any("received response" in m for _, m in rt._logs)


def test_ready_check_alive_http_error_raises_not_ready():
    rt = make_runtime(runtime_id="rid-error")
    runtime_data = {"runtime_id": "rid-error", "pod_status": "READY"}  # case-insensitive
    rt._send_runtime_api_request = lambda method, url, **kwargs: make_response(runtime_data)

    def check_if_alive():
        raise httpx.HTTPError("boom")
    rt.check_if_alive = check_if_alive

    with pytest.raises(AgentRuntimeNotReadyError) as exc:
        rt._wait_until_alive_impl()

    assert "Runtime /alive failed to respond with 200" in str(exc.value)
    # ensure warning log was emitted about /alive failed
    assert any("Runtime /alive failed" in m for lvl, m in rt._logs if lvl == "warning")


@pytest.mark.parametrize("status", ["not found", "pending", "running"])
def test_not_ready_statuses_raise(status):
    rt = make_runtime(runtime_id="rid-notready")
    runtime_data = {"runtime_id": "rid-notready", "pod_status": status}
    rt._send_runtime_api_request = lambda method, url, **kwargs: make_response(runtime_data)
    # check_if_alive should not be called in this branch; set to raise if called
    rt.check_if_alive = lambda: (_ for _ in ()).throw(AssertionError("check_if_alive should not be called"))

    with pytest.raises(AgentRuntimeNotReadyError) as exc:
        rt._wait_until_alive_impl()

    assert status in str(exc.value)


@pytest.mark.parametrize(
    "status, expected_msg_substr, expected_exception",
    [
        ("failed", "Runtime is unavailable (status: failed)", AgentRuntimeUnavailableError),
        ("crashloopbackoff", "Runtime crashed and is being restarted", AgentRuntimeUnavailableError),
        ("unknown", "Runtime is unavailable (status: unknown)", AgentRuntimeUnavailableError),
    ],
)
def test_unavailable_statuses(status, expected_msg_substr, expected_exception):
    rt = make_runtime(runtime_id="rid-unavail")
    runtime_data = {"runtime_id": "rid-unavail", "pod_status": status}
    rt._send_runtime_api_request = lambda method, url, **kwargs: make_response(runtime_data)
    rt.check_if_alive = lambda: (_ for _ in ()).throw(AssertionError("check_if_alive should not be called"))

    with pytest.raises(expected_exception) as exc:
        rt._wait_until_alive_impl()

    assert expected_msg_substr.split()[0] in str(exc.value)


def test_unknown_status_logs_and_final_raise_with_restart_info():
    rt = make_runtime(runtime_id="rid-unknown")
    runtime_data = {
        "runtime_id": "rid-unknown",
        "pod_status": "weirdstate",
        "restart_count": 2,
        "restart_reasons": ["oom", "killed"],
    }
    rt._send_runtime_api_request = lambda method, url, **kwargs: make_response(runtime_data)
    rt.check_if_alive = lambda: (_ for _ in ()).throw(AssertionError("check_if_alive should not be called"))

    with pytest.raises(AgentRuntimeNotReadyError):
        rt._wait_until_alive_impl()

    # Validate that restart info was logged
    assert any("Pod restarts" in m for lvl, m in rt._logs if lvl == "debug")
    # Validate that unknown pod status warning was logged
    assert any("Unknown pod status" in m for lvl, m in rt._logs if lvl == "warning")
    # Validate final debug waiting message exists
    assert any("Waiting for runtime pod to be active" in m for lvl, m in rt._logs if lvl == "debug")
