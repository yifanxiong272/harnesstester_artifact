import importlib
import signal
import pytest

# Import the module under test
mod = importlib.import_module("openhands.runtime.impl.cli.cli_runtime")
CLIRuntime = mod.CLIRuntime

class _Recorder:
    def __init__(self):
        self.calls = []


def test_no_pid_round_035(monkeypatch):
    """If the process object has no pid attribute, nothing should be attempted."""
    called = _Recorder()

    # Make any call to getpgid fail the test if invoked
    def fail_getpgid(pid):
        raise AssertionError("getpgid should not be called when pid is None")

    monkeypatch.setattr(mod, "os", mod.os)
    monkeypatch.setattr(mod.os, "getpgid", fail_getpgid)

    class Proc:  # intentionally no pid attribute
        pass

    proc = Proc()

    # Call the unbound function with a dummy self (None). Should return early without error.
    result = CLIRuntime._safe_terminate_process(None, proc)
    assert result is None


def test_killpg_success_round_035(monkeypatch):
    """When PGID lookup succeeds, os.killpg should be called with returned PGID and given signal."""
    recorder = _Recorder()

    def fake_getpgid(pid):
        recorder.calls.append(("getpgid", pid))
        return 999

    def fake_killpg(pgid, sig):
        recorder.calls.append(("killpg", pgid, sig))

    monkeypatch.setattr(mod, "os", mod.os)
    monkeypatch.setattr(mod.os, "getpgid", fake_getpgid)
    monkeypatch.setattr(mod.os, "killpg", fake_killpg)

    class Proc:
        pid = 123

    proc = Proc()

    CLIRuntime._safe_terminate_process(None, proc, signal_to_send=signal.SIGTERM)

    # Ensure we looked up the pgid and then attempted to kill the group with SIGTERM
    assert recorder.calls == [("getpgid", 123), ("killpg", 999, signal.SIGTERM)]


def test_processlookup_fallback_calls_kill_or_terminate_round_035(monkeypatch):
    """If getpgid raises ProcessLookupError, fallback should call process_obj.kill for SIGKILL and terminate for other signals."""
    calls = _Recorder()

    def raise_processlookup(pid):
        calls.calls.append(("getpgid", pid))
        raise ProcessLookupError("gone")

    monkeypatch.setattr(mod, "os", mod.os)
    monkeypatch.setattr(mod.os, "getpgid", raise_processlookup)

    class ProcKill:
        pid = 10
        def kill(self):
            calls.calls.append(("kill", self.pid))
        def terminate(self):
            calls.calls.append(("terminate", self.pid))

    # Test SIGKILL -> kill()
    proc_k = ProcKill()
    CLIRuntime._safe_terminate_process(None, proc_k, signal_to_send=signal.SIGKILL)
    assert ("getpgid", 10) in calls.calls
    assert ("kill", 10) in calls.calls

    # Reset calls and test SIGTERM -> terminate()
    calls.calls.clear()
    proc_t = ProcKill()
    CLIRuntime._safe_terminate_process(None, proc_t, signal_to_send=signal.SIGTERM)
    assert ("getpgid", 10) in calls.calls
    assert ("terminate", 10) in calls.calls


def test_killpg_raises_oserror_fallback_round_035(monkeypatch):
    """If os.killpg raises OSError, fallback path should attempt process_obj.kill/terminate depending on signal."""
    calls = _Recorder()

    def fake_getpgid(pid):
        calls.calls.append(("getpgid", pid))
        return 50

    def fake_killpg(pgid, sig):
        calls.calls.append(("killpg", pgid, sig))
        raise OSError("nope")

    monkeypatch.setattr(mod, "os", mod.os)
    monkeypatch.setattr(mod.os, "getpgid", fake_getpgid)
    monkeypatch.setattr(mod.os, "killpg", fake_killpg)

    class Proc:
        pid = 5
        def kill(self):
            calls.calls.append(("kill", self.pid))
        def terminate(self):
            calls.calls.append(("terminate", self.pid))

    # For SIGTERM (default in this test) should call terminate()
    proc = Proc()
    CLIRuntime._safe_terminate_process(None, proc, signal_to_send=signal.SIGTERM)
    assert ("getpgid", 5) in calls.calls
    assert ("killpg", 50, signal.SIGTERM) in calls.calls
    assert ("terminate", 5) in calls.calls

    # For SIGKILL should call kill()
    calls.calls.clear()
    proc2 = Proc()
    try:
        CLIRuntime._safe_terminate_process(None, proc2, signal_to_send=signal.SIGKILL)
    except Exception:
        pytest.fail("_safe_terminate_process should not propagate OSError fallback failures")
    assert ("getpgid", 5) in calls.calls
    # killpg will be attempted and then kill fallback called
    assert ("killpg", 50, signal.SIGKILL) in calls.calls
    assert ("kill", 5) in calls.calls


def test_keyboardinterrupt_propagates_round_035(monkeypatch):
    """KeyboardInterrupt raised during PGID lookup must be re-raised."""

    def raise_keyboard(pid):
        raise KeyboardInterrupt()

    monkeypatch.setattr(mod, "os", mod.os)
    monkeypatch.setattr(mod.os, "getpgid", raise_keyboard)

    class Proc:
        pid = 1

    with pytest.raises(KeyboardInterrupt):
        CLIRuntime._safe_terminate_process(None, Proc())


def test_generic_exception_logged_round_035(monkeypatch):
    """A generic Exception during PGID lookup should be caught and logged via logger.error."""
    messages = []

    def raise_generic(pid):
        raise Exception("unexpected boom")

    def fake_error(msg):
        # capture the logged error message
        messages.append(msg)

    monkeypatch.setattr(mod, "os", mod.os)
    monkeypatch.setattr(mod.os, "getpgid", raise_generic)
    # patch the module logger to capture error calls
    monkeypatch.setattr(mod, "logger", mod.logger)
    monkeypatch.setattr(mod.logger, "error", fake_error)

    class Proc:
        pid = 77

    # Should not raise, but should have logged the exception message
    CLIRuntime._safe_terminate_process(None, Proc())
    assert any("unexpected boom" in str(m) for m in messages), f"messages was {messages}"
