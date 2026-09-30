import pytest
from types import SimpleNamespace
import openhands.runtime.impl.remote.remote_runtime as rr_mod

RemoteRuntime = rr_mod.RemoteRuntime


def _patch_super_close():
    """Monkeypatch the ActionExecutionClient.close implementation that remote_runtime calls via super().close().
    This records a flag on the instance so tests can assert the super close was invoked without relying on full init.
    """
    def _super_close(self):
        setattr(self, "super_closed", True)
    rr_mod.ActionExecutionClient.close = _super_close


def make_runtime(
    *,
    attach_to_existing=False,
    keep_runtime_alive=False,
    pause_closed_runtimes=False,
    remote_runtime_api_url="http://example.com/api",
    runtime_closed=False,
    send_side_effect=None,
):
    """Create a RemoteRuntime-like instance without calling its real __init__.

    We set only the attributes used by RemoteRuntime.close.
    send_side_effect may be a callable that records or raises when invoked; it will be bound to the instance.
    """
    inst = object.__new__(RemoteRuntime)

    # Minimal config sandbox namespace expected by close()
    inst.config = SimpleNamespace(sandbox=SimpleNamespace(
        keep_runtime_alive=keep_runtime_alive,
        pause_closed_runtimes=pause_closed_runtimes,
        remote_runtime_api_url=remote_runtime_api_url,
    ))

    inst.attach_to_existing = attach_to_existing
    inst._runtime_closed = runtime_closed
    inst.runtime_id = "rid-123"

    # Capture logs for assertions
    inst._log_entries = []

    def _log(level, message, exc_info=None):
        inst._log_entries.append((level, message))
    inst.log = _log

    # Provide a send implementation (or raising) on the instance to avoid network calls.
    calls = []

    def _send_runtime_api_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if callable(send_side_effect):
            return send_side_effect()
        return {"status": "ok"}

    inst._send_runtime_api_request = _send_runtime_api_request
    inst._send_calls = calls

    # Ensure super().close() behavior is observable
    _patch_super_close()

    return inst


def test_attach_to_existing_calls_super_close_round_056():
    rt = make_runtime(attach_to_existing=True)

    # If attach_to_existing is True, close should call super().close() and return early.
    rt.close()

    assert getattr(rt, "super_closed", False) is True
    # No network calls should have been made
    assert rt._send_calls == []


def test_keep_alive_pause_pauses_runtime_round_056():
    rt = make_runtime(attach_to_existing=False, keep_runtime_alive=True, pause_closed_runtimes=True, runtime_closed=False)

    rt.close()

    # Should have attempted to pause the runtime
    assert len(rt._send_calls) == 1
    method, url, kwargs = rt._send_calls[0]
    assert method == "POST"
    assert url.endswith("/pause")
    assert kwargs.get("json") == {"runtime_id": rt.runtime_id}

    # Should have logged the pause
    assert ("info", "Runtime paused.") in rt._log_entries

    # And should have invoked super().close()
    assert getattr(rt, "super_closed", False) is True


def test_pause_raises_logs_and_propagates_round_056():
    def raise_send():
        raise RuntimeError("boom")

    rt = make_runtime(attach_to_existing=False, keep_runtime_alive=True, pause_closed_runtimes=True, runtime_closed=False, send_side_effect=raise_send)

    with pytest.raises(RuntimeError, match="boom"):
        rt.close()

    # Error should be logged
    # check that an error log was recorded and contains the original message
    assert any(level == "error" and "Unable to pause runtime" in msg and "boom" in msg for level, msg in rt._log_entries)

    # Because the exception is re-raised before calling super().close(), super_closed should not be set
    assert not getattr(rt, "super_closed", False)


def test_stop_when_not_closed_calls_stop_and_finally_closes_round_056():
    rt = make_runtime(attach_to_existing=False, keep_runtime_alive=False, runtime_closed=False)

    rt.close()

    # Should have sent a stop request
    assert len(rt._send_calls) == 1
    method, url, kwargs = rt._send_calls[0]
    assert method == "POST"
    assert url.endswith("/stop")
    assert kwargs.get("json") == {"runtime_id": rt.runtime_id}

    # Should have logged stop
    assert ("info", "Runtime stopped.") in rt._log_entries

    # And finally should call super().close()
    assert getattr(rt, "super_closed", False) is True


def test_stop_raises_logs_and_finally_closes_round_056():
    def raise_stop():
        raise RuntimeError("stopfail")

    rt = make_runtime(attach_to_existing=False, keep_runtime_alive=False, runtime_closed=False, send_side_effect=raise_stop)

    with pytest.raises(RuntimeError, match="stopfail"):
        rt.close()

    # Error log should be recorded
    assert any(level == "error" and "Unable to stop runtime" in msg and "stopfail" in msg for level, msg in rt._log_entries)

    # even on exception, finally should call super().close()
    assert getattr(rt, "super_closed", False) is True


def test_stop_when_already_closed_no_send_but_closes_round_056():
    rt = make_runtime(attach_to_existing=False, keep_runtime_alive=False, runtime_closed=True)

    rt.close()

    # No send calls because runtime was already closed
    assert rt._send_calls == []

    # No "Runtime stopped." info logged
    assert not any(level == "info" and msg == "Runtime stopped." for level, msg in rt._log_entries)

    # But super().close() should still be called from finally
    assert getattr(rt, "super_closed", False) is True
