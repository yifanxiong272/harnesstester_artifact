import pytest
from types import SimpleNamespace
import httpx

from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime
from openhands.core.exceptions import (
    AgentRuntimeNotReadyError,
    AgentRuntimeUnavailableError,
)

# Bind the implementation function for direct calling
_wait_impl = RemoteRuntime._wait_until_alive_impl


def make_fake_runtime(runtime_id, runtime_url="http://x", api_url="http://api"):
    """Create a minimal fake 'self' suitable to call _wait_until_alive_impl.

    It provides attributes and methods referenced by the implementation and
    captures logs in ._logs for assertions.
    """
    obj = SimpleNamespace()
    obj.runtime_id = runtime_id
    obj.runtime_url = runtime_url
    obj.config = SimpleNamespace(sandbox=SimpleNamespace(remote_runtime_api_url=api_url))
    obj._logs = []

    def log(level, message, exc_info=None):
        # store messages for assertions
        obj._logs.append((level, str(message)))

    obj.log = log

    # default send method will be assigned by tests as needed
    def _send_runtime_api_request(method, url, **kwargs):
        raise RuntimeError("_send_runtime_api_request not set in fake runtime")

    obj._send_runtime_api_request = _send_runtime_api_request

    # default check_if_alive to be overwritten in tests
    def check_if_alive():
        return True

    obj.check_if_alive = check_if_alive
    return obj


def test_wait_until_alive_ready_success_round_033():
    """When pod_status is 'ready' and /alive succeeds, the method returns None and logs pod status.

    Covers the 'ready' branch where check_if_alive does not raise.
    """
    fake = make_fake_runtime("rid-1")

    runtime_data = {
        "runtime_id": "rid-1",
        "pod_status": "Ready",
        "restart_count": 0,
    }

    fake._send_runtime_api_request = lambda method, url, **kw: SimpleNamespace(json=lambda: runtime_data)
    # make check_if_alive succeed
    fake.check_if_alive = lambda: True

    # Should not raise
    result = _wait_impl(fake)
    assert result is None

    # ensure log captured the pod status in lowercase as the implementation lowercases it
    assert any("Pod status: ready" in msg for level, msg in fake._logs)


def test_wait_until_alive_ready_http_error_round_033():
    """If pod_status is 'ready' but check_if_alive raises httpx.HTTPError,
    the implementation logs a warning and raises AgentRuntimeNotReadyError.

    This covers the exception handling path inside the 'ready' branch.
    """
    fake = make_fake_runtime("rid-2")

    runtime_data = {
        "runtime_id": "rid-2",
        "pod_status": "ready",
        "restart_count": 0,
    }

    fake._send_runtime_api_request = lambda method, url, **kw: SimpleNamespace(json=lambda: runtime_data)

    def raise_http_error():
        raise httpx.HTTPError("alive-failed")

    fake.check_if_alive = raise_http_error

    with pytest.raises(AgentRuntimeNotReadyError) as excinfo:
        _wait_impl(fake)

    # ensure the original HTTPError message is included in the logged warning and in the raised exception message
    assert any("Runtime /alive failed" in msg for level, msg in fake._logs)
    assert "alive-failed" in str(excinfo.value)


def test_wait_until_alive_running_with_restarts_round_033():
    """If pod_status indicates not-ready states like 'running' and restart_count != 0,
    the implementation should log restart reasons and raise AgentRuntimeNotReadyError.

    This covers the restart_count != 0 branch and the 'running' not-ready branch.
    """
    fake = make_fake_runtime("rid-3")

    runtime_data = {
        "runtime_id": "rid-3",
        "pod_status": "running",
        "restart_count": 2,
        "restart_reasons": ["oom-kill", "evicted"],
    }

    fake._send_runtime_api_request = lambda method, url, **kw: SimpleNamespace(json=lambda: runtime_data)

    with pytest.raises(AgentRuntimeNotReadyError) as excinfo:
        _wait_impl(fake)

    # restart reasons should have been logged
    assert any("Pod restarts:" in msg for level, msg in fake._logs)
    # message should include runtime id and status
    assert "rid-3" in str(excinfo.value)
    assert "running" in str(excinfo.value)


def test_wait_until_alive_crashloopbackoff_round_033():
    """If pod_status is 'crashloopbackoff' the method raises AgentRuntimeUnavailableError
    with the specific crash message.

    This covers the crashloopbackoff branch.
    """
    fake = make_fake_runtime("rid-4")

    runtime_data = {
        "runtime_id": "rid-4",
        "pod_status": "crashloopbackoff",
        "restart_count": 0,
    }

    fake._send_runtime_api_request = lambda method, url, **kw: SimpleNamespace(json=lambda: runtime_data)

    with pytest.raises(AgentRuntimeUnavailableError) as excinfo:
        _wait_impl(fake)

    assert "crashed and is being restarted" in str(excinfo.value)


def test_wait_until_alive_unknown_status_round_033():
    """If pod_status is unknown the method logs a warning and eventually raises AgentRuntimeNotReadyError
    (final fallback at the end of the function).

    This covers the final 'else' path for unknown pod statuses and the final raise at the bottom.
    """
    fake = make_fake_runtime("rid-5")

    runtime_data = {
        "runtime_id": "rid-5",
        "pod_status": "mystery-state",
        "restart_count": 0,
    }

    fake._send_runtime_api_request = lambda method, url, **kw: SimpleNamespace(json=lambda: runtime_data)

    with pytest.raises(AgentRuntimeNotReadyError) as excinfo:
        _wait_impl(fake)

    # Unknown pod status should be logged as a warning
    assert any("Unknown pod status" in msg for level, msg in fake._logs)
    # final raised exception has no message in the code path (AgentRuntimeNotReadyError())
    assert str(excinfo.value) == ""
