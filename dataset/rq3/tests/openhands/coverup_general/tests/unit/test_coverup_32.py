# file: openhands/runtime/impl/cli/cli_runtime.py:227-296
# asked: {"lines": [234, 235, 236, 238, 239, 240, 241, 243, 244, 247, 249, 250, 251, 253, 254, 256, 257, 258, 260, 261, 262, 264, 265, 266, 268, 269, 270, 272, 273, 274, 276, 277, 278, 281, 282, 283, 285, 286, 287, 289, 290, 291, 293, 294, 295, 296], "branches": [[235, 236], [235, 238], [265, 266], [265, 268], [282, 283], [282, 285]]}
# gained: {"lines": [234, 235, 236, 238, 239, 240, 241, 243, 244, 247, 249, 250, 251, 253, 254, 256, 257, 258, 260, 261, 262, 264, 265, 266, 268, 269, 270, 272, 273, 274, 276, 277, 278, 281, 282, 283, 285, 286, 287, 289, 290, 291, 293, 294, 295, 296], "branches": [[235, 236], [235, 238], [265, 266], [265, 268], [282, 283], [282, 285]]}

import os
import signal
import pytest

from openhands.runtime.impl.cli.cli_runtime import CLIRuntime


class FakeProcess:
    def __init__(self, pid, kill_behavior=None, terminate_behavior=None):
        self.pid = pid
        self.killed = False
        self.terminated = False
        # Behaviors can be callables or exceptions to raise
        self._kill_behavior = kill_behavior
        self._terminate_behavior = terminate_behavior

    def kill(self):
        if isinstance(self._kill_behavior, Exception):
            raise self._kill_behavior
        if callable(self._kill_behavior):
            return self._kill_behavior()
        self.killed = True

    def terminate(self):
        if isinstance(self._terminate_behavior, Exception):
            raise self._terminate_behavior
        if callable(self._terminate_behavior):
            return self._terminate_behavior()
        self.terminated = True


def test_no_pid_returns_none():
    # process object without pid attribute -> should return immediately (None)
    class NoPid:
        pass

    res = CLIRuntime._safe_terminate_process(None, NoPid())
    assert res is None


def test_killpg_success_calls_killpg_for_sigterm(monkeypatch):
    calls = {}

    def fake_getpgid(pid):
        calls['got'] = pid
        return 555

    def fake_killpg(pgid, sig):
        calls['killpg'] = (pgid, sig)

    monkeypatch.setattr(os, "getpgid", fake_getpgid)
    monkeypatch.setattr(os, "killpg", fake_killpg)

    p = FakeProcess(123)
    res = CLIRuntime._safe_terminate_process(None, p, signal_to_send=signal.SIGTERM)
    assert res is None
    assert calls['got'] == 123
    assert calls['killpg'] == (555, signal.SIGTERM)
    # ensure direct process methods were not called
    assert not p.killed and not p.terminated


def test_killpg_success_calls_killpg_for_sigkill(monkeypatch):
    calls = {}

    def fake_getpgid(pid):
        calls['got'] = pid
        return 777

    def fake_killpg(pgid, sig):
        calls['killpg'] = (pgid, sig)

    monkeypatch.setattr(os, "getpgid", fake_getpgid)
    monkeypatch.setattr(os, "killpg", fake_killpg)

    p = FakeProcess(222)
    res = CLIRuntime._safe_terminate_process(None, p, signal_to_send=signal.SIGKILL)
    assert res is None
    assert calls['got'] == 222
    assert calls['killpg'] == (777, signal.SIGKILL)
    assert not p.killed and not p.terminated


def test_processlookup_fallback_terminate(monkeypatch):
    # os.getpgid raises ProcessLookupError -> should call process_obj.terminate for SIGTERM
    def fake_getpgid(pid):
        raise ProcessLookupError("no such pid")

    monkeypatch.setattr(os, "getpgid", fake_getpgid)

    p = FakeProcess(321)
    res = CLIRuntime._safe_terminate_process(None, p, signal_to_send=signal.SIGTERM)
    assert res is None
    assert p.terminated is True
    assert p.killed is False


def test_processlookup_fallback_kill_raises_and_is_handled(monkeypatch):
    # os.getpgid raises ProcessLookupError and kill raises -> should be caught and not re-raised
    def fake_getpgid(pid):
        raise ProcessLookupError("gone")

    monkeypatch.setattr(os, "getpgid", fake_getpgid)

    p = FakeProcess(400, kill_behavior=RuntimeError("kill failed"))
    # Should not raise despite kill raising inside fallback; method swallows fallback exceptions
    res = CLIRuntime._safe_terminate_process(None, p, signal_to_send=signal.SIGKILL)
    assert res is None
    # since kill raised, killed flag remains False
    assert p.killed is False


def test_oserror_fallback_terminate_success(monkeypatch):
    # os.getpgid raises OSError -> should be caught and call process_obj.terminate
    def fake_getpgid(pid):
        raise OSError("os error")

    monkeypatch.setattr(os, "getpgid", fake_getpgid)

    p = FakeProcess(888)
    res = CLIRuntime._safe_terminate_process(None, p, signal_to_send=signal.SIGTERM)
    assert res is None
    assert p.terminated is True


def test_oserror_fallback_kill_raises_and_is_handled(monkeypatch):
    # os.getpgid raises AttributeError -> fallback kill raises and is handled
    def fake_getpgid(pid):
        raise AttributeError("attr error")

    monkeypatch.setattr(os, "getpgid", fake_getpgid)

    p = FakeProcess(999, kill_behavior=RuntimeError("boom"))
    res = CLIRuntime._safe_terminate_process(None, p, signal_to_send=signal.SIGKILL)
    assert res is None
    assert p.killed is False


def test_keyboardinterrupt_reraised(monkeypatch):
    # os.getpgid raises KeyboardInterrupt -> should be re-raised
    def fake_getpgid(pid):
        raise KeyboardInterrupt()

    monkeypatch.setattr(os, "getpgid", fake_getpgid)

    p = FakeProcess(42)
    with pytest.raises(KeyboardInterrupt):
        CLIRuntime._safe_terminate_process(None, p, signal_to_send=signal.SIGTERM)


def test_generic_exception_is_logged_and_swallowed(monkeypatch):
    # os.getpgid raises an unexpected exception -> should be caught by the final except and not re-raised
    def fake_getpgid(pid):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(os, "getpgid", fake_getpgid)

    p = FakeProcess(555)
    res = CLIRuntime._safe_terminate_process(None, p, signal_to_send=signal.SIGTERM)
    assert res is None
