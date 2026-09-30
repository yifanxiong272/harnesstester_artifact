import types
import pytest

from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime
from openhands.runtime.impl.action_execution.action_execution_client import ActionExecutionClient


class _Sandbox:
    def __init__(self, keep_runtime_alive=False, pause_closed_runtimes=False, remote_runtime_api_url="http://example.com"):
        self.keep_runtime_alive = keep_runtime_alive
        self.pause_closed_runtimes = pause_closed_runtimes
        self.remote_runtime_api_url = remote_runtime_api_url


class _Config:
    def __init__(self, sandbox: _Sandbox):
        self.sandbox = sandbox


def _make_remote_runtime_instance(
    *,
    attach_to_existing: bool = False,
    keep_runtime_alive: bool = False,
    pause_closed_runtimes: bool = False,
    runtime_closed: bool = False,
    remote_runtime_api_url: str = "http://example.com",
    send_impl=None,
):
    """
    Create a RemoteRuntime instance without calling its real __init__.
    We set only the attributes needed by close().
    """
    inst = object.__new__(RemoteRuntime)
    inst.attach_to_existing = attach_to_existing
    inst.config = _Config(_Sandbox(keep_runtime_alive=keep_runtime_alive, pause_closed_runtimes=pause_closed_runtimes, remote_runtime_api_url=remote_runtime_api_url))
    inst._runtime_closed = runtime_closed
    inst.runtime_id = "runtime-123"

    # simple log recorder
    inst._logged = []

    def _log(level, message, exc_info=None):
        inst._logged.append((level, message))

    inst.log = _log

    # default send implementation: record calls
    calls = []

    def _default_send(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return types.SimpleNamespace(status_code=200)

    inst._send_runtime_api_request = send_impl or _default_send
    inst._send_calls = calls

    return inst


def test_close_attach_to_existing_round_056(monkeypatch):
    # Make sure super().close() is observable and safe to call
    def fake_super_close(self):
        # mark that parent close was invoked
        setattr(self, "_super_closed", True)

    monkeypatch.setattr(ActionExecutionClient, "close", fake_super_close, raising=True)

    inst = _make_remote_runtime_instance(attach_to_existing=True)

    # Call close -> should call super().close() and return without calling send
    inst.close()

    assert getattr(inst, "_super_closed", False) is True
    assert inst._send_calls == []


def test_close_pause_success_round_056(monkeypatch):
    def fake_super_close(self):
        setattr(self, "_super_closed", True)

    monkeypatch.setattr(ActionExecutionClient, "close", fake_super_close, raising=True)

    recorded = []

    def send_impl(method, url, **kwargs):
        recorded.append((method, url, kwargs))
        return types.SimpleNamespace(status_code=200)

    inst = _make_remote_runtime_instance(
        attach_to_existing=False,
        keep_runtime_alive=True,
        pause_closed_runtimes=True,
        runtime_closed=False,
        remote_runtime_api_url="http://api.local",
        send_impl=send_impl,
    )

    inst.close()

    # send should be invoked exactly once to the pause endpoint
    assert len(recorded) == 1
    method, url, kwargs = recorded[0]
    assert method == "POST"
    assert url.endswith("/pause")
    assert kwargs.get("json") == {"runtime_id": inst.runtime_id}

    # info log for paused runtime should be present
    assert ("info", "Runtime paused.") in inst._logged
    assert getattr(inst, "_super_closed", False) is True


def test_close_pause_send_raises_round_056(monkeypatch):
    def fake_super_close(self):
        setattr(self, "_super_closed", True)

    monkeypatch.setattr(ActionExecutionClient, "close", fake_super_close, raising=True)

    def send_impl(method, url, **kwargs):
        raise RuntimeError("boom")

    inst = _make_remote_runtime_instance(
        attach_to_existing=False,
        keep_runtime_alive=True,
        pause_closed_runtimes=True,
        runtime_closed=False,
        remote_runtime_api_url="http://api.local",
        send_impl=send_impl,
    )

    with pytest.raises(RuntimeError):
        inst.close()

    # error log should include the exception message
    assert any(level == "error" and "Unable to pause runtime: boom" in msg for level, msg in inst._logged)

    # super().close() should NOT have been called because exception propagates before that line
    assert getattr(inst, "_super_closed", False) is False


def test_close_stop_success_round_056(monkeypatch):
    def fake_super_close(self):
        setattr(self, "_super_closed", True)

    monkeypatch.setattr(ActionExecutionClient, "close", fake_super_close, raising=True)

    recorded = []

    def send_impl(method, url, **kwargs):
        recorded.append((method, url, kwargs))
        return types.SimpleNamespace(status_code=200)

    inst = _make_remote_runtime_instance(
        attach_to_existing=False,
        keep_runtime_alive=False,
        runtime_closed=False,
        remote_runtime_api_url="http://api.local",
        send_impl=send_impl,
    )

    inst.close()

    # send should be invoked to the stop endpoint
    assert len(recorded) == 1
    method, url, kwargs = recorded[0]
    assert method == "POST"
    assert url.endswith("/stop")
    assert kwargs.get("json") == {"runtime_id": inst.runtime_id}

    # info log for stopped runtime should be present
    assert ("info", "Runtime stopped.") in inst._logged

    # super().close() is called in finally
    assert getattr(inst, "_super_closed", False) is True


def test_close_stop_send_raises_round_056(monkeypatch):
    def fake_super_close(self):
        setattr(self, "_super_closed", True)

    monkeypatch.setattr(ActionExecutionClient, "close", fake_super_close, raising=True)

    def send_impl(method, url, **kwargs):
        raise RuntimeError("boom")

    inst = _make_remote_runtime_instance(
        attach_to_existing=False,
        keep_runtime_alive=False,
        runtime_closed=False,
        remote_runtime_api_url="http://api.local",
        send_impl=send_impl,
    )

    with pytest.raises(RuntimeError):
        inst.close()

    # error log should include the exception message
    assert any(level == "error" and "Unable to stop runtime: boom" in msg for level, msg in inst._logged)

    # super().close() is still called because the finally block should execute
    assert getattr(inst, "_super_closed", False) is True
