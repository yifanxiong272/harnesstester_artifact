import types
import httpx
import pytest
from types import SimpleNamespace

from openhands.runtime.impl.remote import remote_runtime as rr_module
from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime
from openhands.core.exceptions import (
    AgentRuntimeNotReadyError,
    AgentRuntimeUnavailableError,
)


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class Dummy:
    """Minimal object that provides the attributes/methods used by
    RemoteRuntime._wait_until_alive_impl. We deliberately avoid constructing
    the real RemoteRuntime to keep tests focused and deterministic.
    """

    def __init__(self, runtime_id, url_base, response_data, raise_on_check=None):
        # Minimal attributes referenced by the method
        self.runtime_id = runtime_id
        self.runtime_url = f"{url_base}/runtime/{runtime_id}"
        self.config = SimpleNamespace(sandbox=SimpleNamespace(remote_runtime_api_url=url_base))
        self._response = _FakeResponse(response_data)
        self._raise_on_check = raise_on_check
        self.logged = []

    def log(self, level, message, exc_info=None):
        # capture logs so tests can assert that certain branches executed
        self.logged.append((level, message))

    def _send_runtime_api_request(self, method, url, **kwargs):
        # Assert we are being called with the expected GET and url
        assert method == 'GET'
        assert url.startswith(self.config.sandbox.remote_runtime_api_url)
        return self._response

    def check_if_alive(self):
        if isinstance(self._raise_on_check, Exception):
            raise self._raise_on_check
        return None


def _call_impl(dummy):
    # Bind the unbound function and call with the dummy instance
    impl = RemoteRuntime._wait_until_alive_impl
    return impl(dummy)


def test_ready_and_alive_round_033():
    """pod_status == 'ready' and check_if_alive succeeds => method returns None (no exception)
    """
    data = {"runtime_id": "rid-1", "pod_status": "ready"}
    d = Dummy(runtime_id="rid-1", url_base="http://example.com/api", response_data=data)

    # Should not raise
    _call_impl(d)

    # confirm logs contain received response and pod status
    assert any('received response' in m for _, m in d.logged)
    assert any('Pod status' in m for _, m in d.logged)


def test_ready_but_alive_http_error_round_033():
    """pod_status == 'ready' but check_if_alive raises httpx.HTTPError => AgentRuntimeNotReadyError is raised
    """
    data = {"runtime_id": "rid-2", "pod_status": "ready"}
    # Prepare an httpx.HTTPError to be raised by check_if_alive
    err = httpx.HTTPError('failed-alive')
    d = Dummy(runtime_id="rid-2", url_base="http://example.com/api", response_data=data, raise_on_check=err)

    with pytest.raises(AgentRuntimeNotReadyError) as ei:
        _call_impl(d)

    # message should include the original HTTP error string
    assert 'failed-alive' in str(ei.value)
    # ensure warning log about /alive failing was emitted
    assert any('Runtime /alive failed' in m for level, m in d.logged if level == 'warning')


def test_restart_count_and_pending_round_033():
    """restart_count != 0 triggers logging of restart_reasons then pod_status 'pending' raises NotReady
    """
    data = {
        "runtime_id": "rid-3",
        "pod_status": "pending",
        "restart_count": 2,
        "restart_reasons": ['OOMKilled', 'Crash']
    }
    d = Dummy(runtime_id="rid-3", url_base="http://example.com/api", response_data=data)

    with pytest.raises(AgentRuntimeNotReadyError) as ei:
        _call_impl(d)

    # ensure the restart reasons were logged
    assert any('Pod restarts' in m for level, m in d.logged if level == 'debug')
    assert 'not yet ready' in str(ei.value)


def test_crashloopbackoff_round_033():
    """pod_status == 'crashloopbackoff' should raise AgentRuntimeUnavailableError with specific message
    """
    data = {"runtime_id": "rid-4", "pod_status": "crashloopbackoff"}
    d = Dummy(runtime_id="rid-4", url_base="http://example.com/api", response_data=data)

    with pytest.raises(AgentRuntimeUnavailableError) as ei:
        _call_impl(d)

    assert 'Runtime crashed and is being restarted' in str(ei.value)


@pytest.mark.parametrize('status', ['failed', 'unknown'])
def test_failed_or_unknown_round_033(status):
    """pod_status in ('failed','unknown') goes to the else branch raising unavailable with status in message
    """
    data = {"runtime_id": "rid-5", "pod_status": status}
    d = Dummy(runtime_id="rid-5", url_base="http://example.com/api", response_data=data)

    with pytest.raises(AgentRuntimeUnavailableError) as ei:
        _call_impl(d)

    # message should contain the status
    assert status in str(ei.value)


def test_unexpected_status_round_033():
    """Unknown pod_status falls through to warning log and ultimately raises AgentRuntimeNotReadyError
    """
    data = {"runtime_id": "rid-6", "pod_status": 'very-strange-status'}
    d = Dummy(runtime_id="rid-6", url_base="http://example.com/api", response_data=data)

    with pytest.raises(AgentRuntimeNotReadyError):
        _call_impl(d)

    # ensure unknown status warning was logged
    assert any('Unknown pod status' in m for level, m in d.logged if level == 'warning')
