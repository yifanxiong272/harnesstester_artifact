import pytest
from types import SimpleNamespace
from unittest import mock

from openhands.runtime.impl.remote import remote_runtime as rr

# Helper to create a RemoteRuntime instance without invoking __init__
def make_runtime(*, keep_runtime_alive=False, pause_closed_runtimes=False, runtime_closed=False, attach_to_existing=False):
    R = rr.RemoteRuntime
    inst = object.__new__(R)
    inst.config = SimpleNamespace(sandbox=SimpleNamespace(
        keep_runtime_alive=keep_runtime_alive,
        pause_closed_runtimes=pause_closed_runtimes,
        remote_runtime_api_url="http://api.local"
    ))
    inst.runtime_id = "test-runtime"
    inst._runtime_closed = runtime_closed
    inst.attach_to_existing = attach_to_existing

    # capture logs
    inst.log_messages = []
    def log(level, message, exc_info=None):
        inst.log_messages.append((level, message))
    inst.log = log

    # default sender that records calls
    inst.send_calls = []
    def send(method, url, **kwargs):
        inst.send_calls.append((method, url, kwargs))
        return {"status": "ok"}
    inst._send_runtime_api_request = send

    return inst


def _patch_base_close(monkeypatch):
    # Patch the parent ActionExecutionClient.close so super().close() does not try
    # to perform external actions. Instead it will set an attribute on the
    # instance that we can assert.
    def fake_super_close(self):
        setattr(self, "super_closed", True)
    monkeypatch.setattr(rr.ActionExecutionClient, "close", fake_super_close, raising=True)


def test_attach_to_existing_round_056(monkeypatch):
    _patch_base_close(monkeypatch)
    inst = make_runtime(attach_to_existing=True, runtime_closed=False)

    # Ensure no exception and super().close() is invoked immediately.
    inst.close()

    assert getattr(inst, "super_closed", False) is True
    # No API calls should have been made when attach_to_existing is True
    assert inst.send_calls == []
    assert inst.log_messages == []


def test_keep_alive_pause_success_round_056(monkeypatch):
    _patch_base_close(monkeypatch)
    inst = make_runtime(keep_runtime_alive=True, pause_closed_runtimes=True, runtime_closed=False)

    # Replace sender to record and ensure it's called with pause endpoint
    called = {}
    def fake_send(method, url, **kwargs):
        called['method'] = method
        called['url'] = url
        called['kwargs'] = kwargs
    inst._send_runtime_api_request = fake_send

    inst.close()

    assert called['method'] == 'POST'
    assert called['url'] == f"{inst.config.sandbox.remote_runtime_api_url}/pause"
    assert called['kwargs']['json'] == {'runtime_id': inst.runtime_id}

    # Confirm info log for pause
    assert ('info', 'Runtime paused.') in inst.log_messages

    # super().close must be called after pause branch
    assert getattr(inst, "super_closed", False) is True


def test_keep_alive_pause_raises_round_056(monkeypatch):
    _patch_base_close(monkeypatch)
    inst = make_runtime(keep_runtime_alive=True, pause_closed_runtimes=True, runtime_closed=False)

    # Make the send raise to trigger the except path
    def raising_send(method, url, **kwargs):
        raise RuntimeError("pause-failed")
    inst._send_runtime_api_request = raising_send

    with pytest.raises(RuntimeError, match="pause-failed"):
        inst.close()

    # Error log should be recorded and super().close should NOT have been called
    assert any(level == 'error' and 'Unable to pause runtime' in msg for (level, msg) in inst.log_messages)
    assert getattr(inst, "super_closed", False) is False


def test_keep_alive_no_pause_calls_super_round_056(monkeypatch):
    _patch_base_close(monkeypatch)
    # keep_runtime_alive True but pause_closed_runtimes False -> direct super().close and return
    inst = make_runtime(keep_runtime_alive=True, pause_closed_runtimes=False, runtime_closed=False)

    inst._send_runtime_api_request = lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not be called"))

    inst.close()

    # No send calls and super close invoked
    assert getattr(inst, "super_closed", False) is True
    assert inst.log_messages == []


def test_stop_success_round_056(monkeypatch):
    _patch_base_close(monkeypatch)
    inst = make_runtime(keep_runtime_alive=False, runtime_closed=False)

    # Replace sender to record stop call
    calls = []
    def fake_send(method, url, **kwargs):
        calls.append((method, url, kwargs))
    inst._send_runtime_api_request = fake_send

    inst.close()

    # Should have called stop endpoint
    assert calls, "Expected _send_runtime_api_request to be called"
    method, url, kwargs = calls[0]
    assert method == 'POST'
    assert url == f"{inst.config.sandbox.remote_runtime_api_url}/stop"
    assert kwargs['json'] == {'runtime_id': inst.runtime_id}

    # Info log for stopped runtime
    assert ('info', 'Runtime stopped.') in inst.log_messages

    # finally block should call super().close regardless
    assert getattr(inst, "super_closed", False) is True


def test_stop_raises_finally_calls_super_round_056(monkeypatch):
    _patch_base_close(monkeypatch)
    inst = make_runtime(keep_runtime_alive=False, runtime_closed=False)

    def raising_send(method, url, **kwargs):
        raise RuntimeError("stop-err")
    inst._send_runtime_api_request = raising_send

    with pytest.raises(RuntimeError, match="stop-err"):
        inst.close()

    # Error should be logged
    assert any(level == 'error' and 'Unable to stop runtime' in msg for (level, msg) in inst.log_messages)

    # finally block must still execute super().close
    assert getattr(inst, "super_closed", False) is True


def test_stop_already_closed_skips_request_round_056(monkeypatch):
    _patch_base_close(monkeypatch)
    # If runtime already closed, no stop request should be sent
    inst = make_runtime(keep_runtime_alive=False, runtime_closed=True)

    called = {'sent': False}
    def fake_send(method, url, **kwargs):
        called['sent'] = True
    inst._send_runtime_api_request = fake_send

    inst.close()

    assert called['sent'] is False
    assert getattr(inst, "super_closed", False) is True
