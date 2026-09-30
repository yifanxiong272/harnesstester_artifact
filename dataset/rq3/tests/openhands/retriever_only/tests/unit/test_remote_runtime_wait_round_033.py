import types
from types import SimpleNamespace, MethodType
import pytest
import httpx

from openhands.core.exceptions import (
    AgentRuntimeNotReadyError,
    AgentRuntimeUnavailableError,
)
import importlib

# Import the RemoteRuntime class only to obtain the function object to bind
remote_mod = importlib.import_module('openhands.runtime.impl.remote.remote_runtime')
RemoteRuntime = remote_mod.RemoteRuntime
_wait_fn = RemoteRuntime._wait_until_alive_impl


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def make_dummy(runtime_data, check_if_alive=None):
    """Create a dummy 'self' object with attributes used by _wait_until_alive_impl.

    Returns a tuple (bound_method, log_calls) where bound_method is the
    _wait_until_alive_impl bound to the dummy and log_calls is a list of logged
    (level, message) pairs for assertions.
    """
    dummy = SimpleNamespace()
    # attributes referenced in function
    dummy.runtime_url = 'http://dummy-runtime-url'
    dummy.runtime_id = runtime_data.get('runtime_id', 'rid')
    dummy.config = SimpleNamespace(sandbox=SimpleNamespace(remote_runtime_api_url='http://api'))

    log_calls = []

    def log(level, message, exc_info=None):
        # store messages for inspection
        log_calls.append((level, str(message)))

    dummy.log = log

    # _send_runtime_api_request should return an object with .json()
    def _send_runtime_api_request(method, url, **kwargs):
        return FakeResponse(runtime_data)

    dummy._send_runtime_api_request = _send_runtime_api_request

    # check_if_alive may be provided; default is a no-op (success)
    if check_if_alive is None:
        def _check():
            return None

        dummy.check_if_alive = _check
    else:
        dummy.check_if_alive = check_if_alive

    # bind the function to this dummy instance
    bound = MethodType(_wait_fn, dummy)
    return bound, log_calls


def test_ready_check_alive_succeeds_round_033():
    runtime_data = {'runtime_id': 'rid-1', 'pod_status': 'ready'}
    bound, logs = make_dummy(runtime_data)

    # Should return None and not raise
    result = bound()
    assert result is None

    # Check that we logged pod status and received response
    msgs = "\n".join(m for _, m in logs)
    assert 'Pod status: ready' in msgs
    assert "received response" in msgs or "received response:" in msgs


def test_ready_check_alive_http_error_round_033():
    runtime_data = {'runtime_id': 'rid-2', 'pod_status': 'ready'}

    def raising_check():
        raise httpx.HTTPError('alive failed')

    bound, logs = make_dummy(runtime_data, check_if_alive=raising_check)

    with pytest.raises(AgentRuntimeNotReadyError) as excinfo:
        bound()

    # When /alive fails we should have a warning log about /alive failure
    msgs = "\n".join(m for _, m in logs)
    assert 'Runtime /alive failed' in msgs or 'Runtime /alive failed, but pod says it\'s ready' in msgs
    assert 'alive failed' in str(excinfo.value)


def test_running_with_restarts_round_033():
    runtime_data = {
        'runtime_id': 'rid-3',
        'pod_status': 'running',
        'restart_count': 2,
        'restart_reasons': ['oom', 'killed'],
    }
    bound, logs = make_dummy(runtime_data)

    with pytest.raises(AgentRuntimeNotReadyError) as excinfo:
        bound()

    # Confirm restart-related logging happened
    msgs = "\n".join(m for _, m in logs)
    assert 'Pod restarts' in msgs or 'restart' in msgs
    assert 'Status: running' in str(excinfo.value)


def test_crashloopbackoff_unavailable_round_033():
    runtime_data = {'runtime_id': 'rid-4', 'pod_status': 'crashloopbackoff'}
    bound, logs = make_dummy(runtime_data)

    with pytest.raises(AgentRuntimeUnavailableError) as excinfo:
        bound()

    # crashloopbackoff triggers a specific user-facing message
    assert 'crashed and is being restarted' in str(excinfo.value)


def test_failed_unavailable_round_033():
    runtime_data = {'runtime_id': 'rid-5', 'pod_status': 'failed'}
    bound, logs = make_dummy(runtime_data)

    with pytest.raises(AgentRuntimeUnavailableError) as excinfo:
        bound()

    assert 'Runtime is unavailable (status: failed)' in str(excinfo.value)


def test_unknown_status_raises_at_end_round_033():
    # Unknown status should log a warning about unknown pod status and then
    # eventually raise a generic AgentRuntimeNotReadyError at the end.
    runtime_data = {'runtime_id': 'rid-6', 'pod_status': 'weird-status'}
    bound, logs = make_dummy(runtime_data)

    with pytest.raises(AgentRuntimeNotReadyError) as excinfo:
        bound()

    msgs = "\n".join(m for _, m in logs)
    assert 'Unknown pod status' in msgs
    # final exception was raised without a specific message in code -> ensure type
    assert str(excinfo.value) == ''
