import signal
import types
import pytest

import openhands.runtime.impl.cli.cli_runtime as cli_mod

CLIRuntime = cli_mod.CLIRuntime


class _DummyProc:
    def __init__(self, pid=None, kill_side_effect=None, terminate_side_effect=None):
        self.pid = pid
        self._kill_side_effect = kill_side_effect
        self._terminate_side_effect = terminate_side_effect

    def kill(self):
        if callable(self._kill_side_effect):
            return self._kill_side_effect()
        if isinstance(self._kill_side_effect, Exception):
            raise self._kill_side_effect
        return True

    def terminate(self):
        if callable(self._terminate_side_effect):
            return self._terminate_side_effect()
        if isinstance(self._terminate_side_effect, Exception):
            raise self._terminate_side_effect
        return True


def test_pid_none_round_035(monkeypatch):
    """When process_obj.pid is None, nothing should be attempted (no getpgid call).

    This is deterministic: os.getpgid is patched to raise if called.
    """
    proc = _DummyProc(pid=None)

    def _fail_getpgid(_pid):
        raise AssertionError("getpgid should not be called when pid is None")

    monkeypatch.setattr(cli_mod.os, "getpgid", _fail_getpgid)

    # Should not raise
    CLIRuntime._safe_terminate_process(None, proc)


def test_successful_killpg_round_035(monkeypatch):
    """When a PGID is found, os.killpg should be called with that PGID and the signal.

    We patch getpgid to return a PGID and replace killpg with a recorder.
    """
    proc = _DummyProc(pid=1234)
    calls = []

    monkeypatch.setattr(cli_mod.os, "getpgid", lambda pid: 4321 if pid == 1234 else pid)

    def _fake_killpg(pgid, sig):
        calls.append((pgid, sig))

    monkeypatch.setattr(cli_mod.os, "killpg", _fake_killpg)

    CLIRuntime._safe_terminate_process(None, proc, signal_to_send=signal.SIGTERM)

    assert calls == [(4321, signal.SIGTERM)], "os.killpg should be called with PGID and SIGTERM"


def test_pgid_missing_fallback_kill_round_035(monkeypatch):
    """If getpgid raises ProcessLookupError and signal is SIGKILL, process_obj.kill() should be called.
    """
    proc = _DummyProc(pid=42)
    called = {"kill": False, "terminate": False}

    def _mark_kill():
        called["kill"] = True

    def _fail_getpgid(pid):
        raise ProcessLookupError("no such process")

    proc._kill_side_effect = _mark_kill

    monkeypatch.setattr(cli_mod.os, "getpgid", _fail_getpgid)

    CLIRuntime._safe_terminate_process(None, proc, signal_to_send=signal.SIGKILL)

    assert called["kill"] is True and called["terminate"] is False


def test_pgid_missing_fallback_terminate_round_035(monkeypatch):
    """If getpgid raises ProcessLookupError and signal is SIGTERM, process_obj.terminate() should be called.
    """
    proc = _DummyProc(pid=43)
    called = {"kill": False, "terminate": False}

    def _mark_terminate():
        called["terminate"] = True

    def _fail_getpgid(pid):
        raise ProcessLookupError("gone")

    proc._terminate_side_effect = _mark_terminate

    monkeypatch.setattr(cli_mod.os, "getpgid", _fail_getpgid)

    CLIRuntime._safe_terminate_process(None, proc, signal_to_send=signal.SIGTERM)

    assert called["terminate"] is True and called["kill"] is False


def test_getpgid_oserror_fallback_and_fallback_raises_round_035(monkeypatch):
    """If getpgid raises OSError, and the fallback terminate raises an exception, the method should swallow it
    and log an error (logger.error called with a message containing fallback error text).
    """
    proc = _DummyProc(pid=99)

    def _fail_getpgid(pid):
        raise OSError("bad getpgid")

    def _raise_on_terminate():
        raise RuntimeError("terminate failed")

    proc._terminate_side_effect = _raise_on_terminate

    errors = []

    def _capture_error(msg, *args, **kwargs):
        # logger.error may be called with a single formatted string
        try:
            errors.append(str(msg))
        except Exception:
            errors.append(repr(msg))

    monkeypatch.setattr(cli_mod.os, "getpgid", _fail_getpgid)
    monkeypatch.setattr(cli_mod.logger, "error", _capture_error)

    # Call with SIGTERM so code paths go to 'terminate' branch in fallback
    CLIRuntime._safe_terminate_process(None, proc, signal_to_send=signal.SIGTERM)

    assert any("Fallback: Error during terminate" in e or "terminate failed" in e for e in errors), (
        "logger.error should be invoked with a message about fallback terminate failure"
    )
