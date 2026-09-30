import types
import httpx
import pytest
from openhands.core.exceptions import (
    AgentRuntimeNotReadyError,
    AgentRuntimeUnavailableError,
)

# We import the function under test as a bound function; however, to avoid
# constructing a full RemoteRuntime we will call the method with a fake
# self object that provides the exact attributes used by the implementation.
from openhands.runtime.impl.remote import remote_runtime as rr_module


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def _make_fake_self(runtime_id: str, pod_status: str, restart_count: int = 0, restart_reasons=None, check_alive_side_effect=None):
    """Construct a minimal fake `self` object matching what _wait_until_alive_impl expects.

    - runtime_url: used in initial debug log
    - config.sandbox.remote_runtime_api_url: used to build URL for _send_runtime_api_request
    - runtime_id: must match runtime_data['runtime_id'] assertion in method
    - _send_runtime_api_request: returns object with json() method
    - check_if_alive: callable which may raise httpx.HTTPError
    - log: simple collector of (level, message) tuples
    """
    logs = []

    def log(level, message, exc_info=None):
        # store the messages for assertions
        logs.append((level, str(message)))

    sandbox = types.SimpleNamespace(remote_runtime_api_url="https://api.example.invalid")
    config = types.SimpleNamespace(sandbox=sandbox)

    data = {
        "runtime_id": runtime_id,
        "pod_status": pod_status,
    }
    if restart_count is not None:
        data["restart_count"] = restart_count
    if restart_reasons is not None:
        data["restart_reasons"] = restart_reasons

    def _send_runtime_api_request(method, url):
        # verify URL contains the configured base and runtime id to ensure the
        # code under test built the URL as expected
        assert sandbox.remote_runtime_api_url in url
        assert runtime_id in url
        return _FakeResponse(data)

    def _check_if_alive():
        if isinstance(check_alive_side_effect, Exception):
            raise check_alive_side_effect
        if callable(check_alive_side_effect):
            return check_alive_side_effect()
        return None

    fake = types.SimpleNamespace(
        log=log,
        config=config,
        runtime_id=runtime_id,
        runtime_url=f"https://ui.example.invalid/runtimes/{runtime_id}",
        _send_runtime_api_request=_send_runtime_api_request,
        check_if_alive=_check_if_alive,
        _logs=logs,
    )

    return fake


def test_ready_with_check_alive_failure_round_033():
    """When pod_status is 'ready' but check_if_alive raises an httpx.HTTPError,
    the implementation should log a warning and raise AgentRuntimeNotReadyError.
    """
    fake = _make_fake_self(
        runtime_id="rid-123",
        pod_status="ready",
        restart_count=0,
        check_alive_side_effect=httpx.HTTPError("alive failed"),
    )

    with pytest.raises(AgentRuntimeNotReadyError) as excinfo:
        rr_module.RemoteRuntime._wait_until_alive_impl(fake)

    # Confirm that the raised exception mentions the underlying error text
    assert "alive failed" in str(excinfo.value)

    # The logs should include a warning about /alive failing while the pod says ready
    warnings = [m for (lvl, m) in fake._logs if lvl == "warning"]
    assert any("Runtime /alive failed, but pod says it's ready" in w for w in warnings)


def test_restart_count_nonzero_leads_to_unavailable_round_033():
    """If restart_count != 0 and pod_status is in the unavailable group (e.g. 'unknown'),
    the function should log the restart reasons and raise AgentRuntimeUnavailableError.
    """
    fake = _make_fake_self(
        runtime_id="rid-456",
        pod_status="unknown",
        restart_count=2,
        restart_reasons=["oom", "killed"],
        check_alive_side_effect=None,
    )

    with pytest.raises(AgentRuntimeUnavailableError) as excinfo:
        rr_module.RemoteRuntime._wait_until_alive_impl(fake)

    # The log should include the restart summary
    debug_msgs = [m for (lvl, m) in fake._logs if lvl == "debug"]
    assert any("Pod restarts: 2" in m and "['oom', 'killed']" in m for m in debug_msgs)

    # The exception should indicate unavailability
    assert "Runtime is unavailable" in str(excinfo.value) or isinstance(excinfo.value, AgentRuntimeUnavailableError)


def test_pending_status_raises_not_ready_round_033():
    """pod_status 'pending' should raise AgentRuntimeNotReadyError with a helpful message.
    """
    rid = "rid-789"
    fake = _make_fake_self(runtime_id=rid, pod_status="pending", restart_count=0)

    with pytest.raises(AgentRuntimeNotReadyError) as excinfo:
        rr_module.RemoteRuntime._wait_until_alive_impl(fake)

    assert rid in str(excinfo.value)
    assert "pending" in str(excinfo.value)


def test_crashloopbackoff_raises_unavailable_round_033():
    """pod_status 'crashloopbackoff' maps to a specific AgentRuntimeUnavailableError message.
    """
    fake = _make_fake_self(runtime_id="rid-crash", pod_status="crashloopbackoff", restart_count=0)

    with pytest.raises(AgentRuntimeUnavailableError) as excinfo:
        rr_module.RemoteRuntime._wait_until_alive_impl(fake)

    assert "Runtime crashed and is being restarted" in str(excinfo.value)


def test_unknown_pod_status_logs_and_raises_round_033():
    """An unrecognized pod_status should log a warning 'Unknown pod status' and then
    ultimately raise AgentRuntimeNotReadyError from the fallback at the end of the method.
    """
    fake = _make_fake_self(runtime_id="rid-unk", pod_status="weirdstate", restart_count=0)

    with pytest.raises(AgentRuntimeNotReadyError):
        rr_module.RemoteRuntime._wait_until_alive_impl(fake)

    warnings = [m for (lvl, m) in fake._logs if lvl == "warning"]
    assert any("Unknown pod status" in w for w in warnings)
