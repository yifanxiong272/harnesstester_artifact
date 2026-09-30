# file: openhands/runtime/impl/remote/remote_runtime.py:423-490
# asked: {"lines": [424, 425, 426, 427, 429, 430, 431, 433, 434, 435, 436, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 453, 454, 455, 456, 457, 458, 459, 461, 462, 464, 466, 467, 468, 470, 471, 473, 474, 475, 476, 479, 480, 484, 486, 487, 488, 490], "branches": [[444, 445], [444, 453], [453, 454], [453, 465], [465, 470], [465, 473], [473, 474], [473, 484], [474, 475], [474, 479]]}
# gained: {"lines": [424, 425, 426, 427, 429, 430, 431, 433, 434, 435, 436, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 453, 454, 455, 456, 457, 458, 459, 461, 462, 464, 466, 467, 468, 470, 471, 473, 474, 475, 476, 479, 480, 484, 486, 487, 488, 490], "branches": [[444, 445], [444, 453], [453, 454], [453, 465], [465, 470], [465, 473], [473, 474], [473, 484], [474, 475], [474, 479]]}

import pytest
import types
import httpx

from openhands.core.exceptions import AgentRuntimeNotReadyError, AgentRuntimeUnavailableError
from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime


class DummyResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def make_runtime_with_response(runtime_data):
    # Create object without invoking __init__
    rt = RemoteRuntime.__new__(RemoteRuntime)
    # Minimal attributes used by _wait_until_alive_impl
    rt.runtime_id = runtime_data.get("runtime_id", "rid")
    rt.runtime_url = "http://runtime-url"
    # config with sandbox.remote_runtime_api_url
    rt.config = types.SimpleNamespace(sandbox=types.SimpleNamespace(remote_runtime_api_url="http://api"))
    # logger collector
    rt.logged = []

    def log(level, message, exc_info=None):
        rt.logged.append((level, message))

    rt.log = log

    # _send_runtime_api_request returns DummyResponse with the provided data
    def _send_runtime_api_request(method, url, **kwargs):
        assert method == "GET"
        assert url == f"{rt.config.sandbox.remote_runtime_api_url}/runtime/{rt.runtime_id}"
        return DummyResponse(runtime_data)

    rt._send_runtime_api_request = _send_runtime_api_request

    return rt


def test_ready_and_alive_success():
    runtime_data = {"runtime_id": "r1", "pod_status": "ready", "restart_count": 0}
    rt = make_runtime_with_response(runtime_data)

    # check_if_alive succeeds (no exception)
    rt.check_if_alive = lambda: None

    # Should not raise
    rt._wait_until_alive_impl()


def test_ready_but_alive_http_error_results_in_not_ready_error():
    runtime_data = {"runtime_id": "r2", "pod_status": "ready", "restart_count": 0}
    rt = make_runtime_with_response(runtime_data)

    # check_if_alive raises httpx.HTTPError
    def raise_http_error():
        raise httpx.HTTPError("boom!")

    rt.check_if_alive = raise_http_error

    with pytest.raises(AgentRuntimeNotReadyError) as excinfo:
        rt._wait_until_alive_impl()

    assert "Runtime /alive failed to respond with 200" in str(excinfo.value)
    assert "boom!" in str(excinfo.value)


@pytest.mark.parametrize("status", ["not found", "pending", "running"])
def test_not_ready_statuses_raise_not_ready(status):
    runtime_data = {"runtime_id": "r3", "pod_status": status, "restart_count": 0}
    rt = make_runtime_with_response(runtime_data)

    with pytest.raises(AgentRuntimeNotReadyError) as excinfo:
        rt._wait_until_alive_impl()

    # message should include runtime id and status
    assert f"(ID={rt.runtime_id})" in str(excinfo.value) or status in str(excinfo.value)


def test_unavailable_crashloopbackoff_raises_unavailable_with_specific_message():
    runtime_data = {"runtime_id": "r4", "pod_status": "crashloopbackoff", "restart_count": 0}
    rt = make_runtime_with_response(runtime_data)

    with pytest.raises(AgentRuntimeUnavailableError) as excinfo:
        rt._wait_until_alive_impl()

    assert "Runtime crashed and is being restarted" in str(excinfo.value)


def test_unavailable_failed_raises_generic_unavailable():
    runtime_data = {"runtime_id": "r5", "pod_status": "failed", "restart_count": 0}
    rt = make_runtime_with_response(runtime_data)

    with pytest.raises(AgentRuntimeUnavailableError) as excinfo:
        rt._wait_until_alive_impl()

    assert "Runtime is unavailable (status: failed)" in str(excinfo.value)


def test_unknown_status_with_restarts_logs_and_final_not_ready():
    runtime_data = {
        "runtime_id": "r6",
        "pod_status": "mystatus",
        "restart_count": 2,
        "restart_reasons": "oom"
    }
    rt = make_runtime_with_response(runtime_data)

    # Should log restart reasons (we'll assert logged messages) and finally raise AgentRuntimeNotReadyError
    with pytest.raises(AgentRuntimeNotReadyError):
        rt._wait_until_alive_impl()

    # Check that restart info was logged
    found = any("Pod restarts" in msg for (_lvl, msg) in rt.logged)
    assert found, f"Expected restart log in {rt.logged}"
