import pytest
import signal

from openhands.runtime.impl.cli import cli_runtime as cli_module
from openhands.runtime.impl.cli.cli_runtime import CLIRuntime


class FakeLogger:
    def __init__(self):
        self.debug_calls = []
        self.warning_calls = []
        self.error_calls = []

    def debug(self, msg):
        self.debug_calls.append(msg)

    def warning(self, msg):
        self.warning_calls.append(msg)

    def error(self, msg):
        self.error_calls.append(msg)


def test_pid_none_round_035(monkeypatch):
    """If process_obj.pid is None, nothing else should be called and function should return silently."""
    # Ensure module-level os.getpgid is not called
    def fail_if_called(pid):
        raise AssertionError("getpgid should not be called when pid is None")

    monkeypatch.setattr(cli_module.os, "getpgid", fail_if_called)

    class P:
        pid = None

    # Call unbound method directly; no exception expected
    CLIRuntime._safe_terminate_process(object(), P(), signal.SIGTERM)


def test_success_killpg_round_035(monkeypatch):
    """When PGID is found, os.killpg should be called with that PGID and provided signal."""
    recorded = {}

    def fake_getpgid(pid):
        recorded['pid'] = pid
        return 1001

    def fake_killpg(pgid, sig):
        recorded['killpg'] = (pgid, sig)

    # NOTE: use the correctly named fake_getpgid (previously a typo caused NameError)
    monkeypatch.setattr(cli_module.os, "getpgid", fake_getpgid)
    monkeypatch.setattr(cli_module.os, "killpg", fake_killpg)

    class P:
        def __init__(self):
            self.pid = 42
            self.killed = False
            self.terminated = False

        def kill(self):
            self.killed = True

        def terminate(self):
            self.terminated = True

    p = P()
    CLIRuntime._safe_terminate_process(object(), p, signal.SIGTERM)

    # Ensure getpgid was called for our pid and killpg invoked with returned PGID and SIGTERM
    assert recorded.get('pid') == 42
    assert recorded.get('killpg') == (1001, signal.SIGTERM)

    # Fallback methods should not have been invoked
    assert not p.killed
    assert not p.terminated


def test_getpgid_processlookup_sigkill_round_035(monkeypatch):
    """If os.getpgid raises ProcessLookupError, fallback should call process.kill() for SIGKILL."""
    fake_logger = FakeLogger()
    monkeypatch.setattr(cli_module, 'logger', fake_logger)

    def raise_pl(pid):
        raise ProcessLookupError("no pgid")

    monkeypatch.setattr(cli_module.os, 'getpgid', raise_pl)

    class P:
        def __init__(self):
            self.pid = 10
            self.killed = False

        def kill(self):
            self.killed = True

        def terminate(self):
            raise AssertionError("terminate should not be called for SIGKILL fallback")

    p = P()
    CLIRuntime._safe_terminate_process(object(), p, signal.SIGKILL)

    assert p.killed is True
    # A warning should have been logged about ProcessLookupError
    assert any('ProcessLookupError' in str(m) or 'already exited' in str(m) for m in fake_logger.warning_calls)


def test_getpgid_processlookup_sigkill_failure_round_035(monkeypatch):
    """If fallback .kill() raises, it should be caught and logger.error called."""
    fake_logger = FakeLogger()
    monkeypatch.setattr(cli_module, 'logger', fake_logger)

    def raise_pl(pid):
        raise ProcessLookupError("missing")

    monkeypatch.setattr(cli_module.os, 'getpgid', raise_pl)

    class P:
        def __init__(self):
            self.pid = 11

        def kill(self):
            raise RuntimeError("kill failed")

        def terminate(self):
            # Should not be used in this test
            pass

    p = P()
    # Should not raise despite kill raising internally
    CLIRuntime._safe_terminate_process(object(), p, signal.SIGKILL)

    # The fallback exception should have been logged
    assert any('kill' in str(m) or 'Error during' in str(m) for m in fake_logger.error_calls)


def test_getpgid_raises_oserror_fallback_terminate_round_035(monkeypatch):
    """If os.getpgid raises OSError, fallback should call terminate() for non-SIGKILL and log appropriately if terminate fails."""
    fake_logger = FakeLogger()
    monkeypatch.setattr(cli_module, 'logger', fake_logger)

    def raise_os(pid):
        raise OSError("pgid error")

    monkeypatch.setattr(cli_module.os, 'getpgid', raise_os)

    class P:
        def __init__(self):
            self.pid = 12
            self.terminated = False

        def kill(self):
            raise AssertionError("kill should not be called for SIGTERM fallback")

        def terminate(self):
            self.terminated = True

    p = P()
    CLIRuntime._safe_terminate_process(object(), p, signal.SIGTERM)

    assert p.terminated is True

    # Now simulate terminate raising and ensure it is caught and logged
    def raise_terminate(self):
        raise RuntimeError("terminate failed")

    P2 = type('P2', (), {'pid': 13, 'kill': lambda self: None, 'terminate': raise_terminate})
    p2 = P2()
    CLIRuntime._safe_terminate_process(object(), p2, signal.SIGTERM)
    assert any('Error during' in str(m) or 'terminate' in str(m) for m in fake_logger.error_calls)


def test_getpgid_raises_keyboardinterrupt_round_035(monkeypatch):
    """KeyboardInterrupt raised by os.getpgid should propagate out of the function."""
    def raise_kb(pid):
        raise KeyboardInterrupt()

    monkeypatch.setattr(cli_module.os, 'getpgid', raise_kb)

    class P:
        pid = 99

    with pytest.raises(KeyboardInterrupt):
        CLIRuntime._safe_terminate_process(object(), P(), signal.SIGTERM)


def test_killpg_raises_round_035(monkeypatch):
    """If killpg raises a generic Exception after a successful getpgid, it should be logged by the general except block."""
    fake_logger = FakeLogger()
    monkeypatch.setattr(cli_module, 'logger', fake_logger)

    def fake_getpgid(pid):
        return 2020

    def raise_killpg(pgid, sig):
        raise RuntimeError('killpg failed')

    monkeypatch.setattr(cli_module.os, 'getpgid', fake_getpgid)
    monkeypatch.setattr(cli_module.os, 'killpg', raise_killpg)

    class P:
        def __init__(self):
            self.pid = 50

        def kill(self):
            pass

        def terminate(self):
            pass

    p = P()
    # Should not raise; error should be logged in the final except
    CLIRuntime._safe_terminate_process(object(), p, signal.SIGTERM)

    assert any('Error:' in str(m) or 'killpg' in str(m) for m in fake_logger.error_calls)
