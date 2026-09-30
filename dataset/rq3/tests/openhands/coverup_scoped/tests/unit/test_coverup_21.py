# file: openhands/runtime/impl/cli/cli_runtime.py:227-296
# asked: {"lines": [234, 235, 236, 238, 239, 240, 241, 243, 244, 247, 249, 250, 251, 253, 254, 256, 257, 258, 260, 261, 262, 264, 265, 266, 268, 269, 270, 272, 273, 274, 276, 277, 278, 281, 282, 283, 285, 286, 287, 289, 290, 291, 293, 294, 295, 296], "branches": [[235, 236], [235, 238], [265, 266], [265, 268], [282, 283], [282, 285]]}
# gained: {"lines": [234, 235, 236, 238, 239, 240, 241, 243, 244, 247, 249, 250, 251, 253, 254, 256, 257, 258, 260, 261, 262, 264, 265, 266, 268, 269, 270, 272, 273, 274, 276, 277, 278, 281, 282, 285, 286, 287, 293, 294, 295, 296], "branches": [[235, 236], [235, 238], [265, 266], [265, 268], [282, 285]]}

import signal
import os
import pytest

from openhands.runtime.impl.cli.cli_runtime import CLIRuntime


def _make_inst():
    # Create instance without calling __init__
    return object.__new__(CLIRuntime)


def test_safe_terminate_no_pid():
    inst = _make_inst()

    class P:
        pid = None

    proc = P()
    # Should simply return None / do nothing and not raise
    assert inst._safe_terminate_process(proc) is None


def test_safe_terminate_killpg_success(monkeypatch):
    inst = _make_inst()
    captured = {}

    def fake_getpgid(pid):
        captured['pid_in_getpgid'] = pid
        return 4242

    def fake_killpg(pgid, sig):
        captured['killpg_args'] = (pgid, sig)

    monkeypatch.setattr(os, "getpgid", fake_getpgid)
    monkeypatch.setattr(os, "killpg", fake_killpg)

    class P:
        pid = 1234

    proc = P()
    inst._safe_terminate_process(proc, signal.SIGKILL)

    assert captured['pid_in_getpgid'] == 1234
    assert captured['killpg_args'] == (4242, signal.SIGKILL)


def test_safe_terminate_getpgid_processlookup_fallback_terminate(monkeypatch):
    inst = _make_inst()
    # Simulate os.getpgid raising ProcessLookupError -> fallback to terminate
    def fake_getpgid(pid):
        raise ProcessLookupError("no such pid")

    monkeypatch.setattr(os, "getpgid", fake_getpgid)

    class P:
        pid = 2222

        def __init__(self):
            self.terminated = False
            self.killed = False

        def terminate(self):
            self.terminated = True

        def kill(self):
            self.killed = True

    proc = P()
    inst._safe_terminate_process(proc, signal.SIGTERM)
    assert proc.terminated is True
    assert proc.killed is False


def test_safe_terminate_getpgid_processlookup_fallback_kill(monkeypatch):
    inst = _make_inst()

    def fake_getpgid(pid):
        raise ProcessLookupError("gone")

    monkeypatch.setattr(os, "getpgid", fake_getpgid)

    class P:
        pid = 3333

        def __init__(self):
            self.terminated = False
            self.killed = False

        def terminate(self):
            self.terminated = True

        def kill(self):
            self.killed = True

    proc = P()
    inst._safe_terminate_process(proc, signal.SIGKILL)
    assert proc.killed is True
    assert proc.terminated is False


def test_safe_terminate_getpgid_processlookup_fallback_raises_in_fallback(monkeypatch):
    inst = _make_inst()

    def fake_getpgid(pid):
        raise ProcessLookupError("gone")

    monkeypatch.setattr(os, "getpgid", fake_getpgid)

    class P:
        pid = 4444

        def terminate(self):
            raise RuntimeError("terminate failed")

        def kill(self):
            raise RuntimeError("kill failed")

    proc = P()
    # Should not raise despite fallback raising; errors are caught and logged
    inst._safe_terminate_process(proc, signal.SIGTERM)
    inst._safe_terminate_process(proc, signal.SIGKILL)


def test_safe_terminate_oserror_in_killpg_then_fallback(monkeypatch):
    inst = _make_inst()
    captured = {}

    def fake_getpgid(pid):
        captured['pid'] = pid
        return 7777

    def fake_killpg(pgid, sig):
        raise OSError("killpg failed")

    monkeypatch.setattr(os, "getpgid", fake_getpgid)
    monkeypatch.setattr(os, "killpg", fake_killpg)

    class P:
        pid = 8888

        def __init__(self):
            self.terminated = False
            self.killed = False

        def terminate(self):
            self.terminated = True

        def kill(self):
            self.killed = True

    proc = P()
    inst._safe_terminate_process(proc, signal.SIGTERM)
    assert proc.terminated is True
    assert proc.killed is False


def test_safe_terminate_keyboardinterrupt_propagates(monkeypatch):
    inst = _make_inst()

    def fake_getpgid(pid):
        raise KeyboardInterrupt()

    monkeypatch.setattr(os, "getpgid", fake_getpgid)

    class P:
        pid = 9999

    proc = P()
    with pytest.raises(KeyboardInterrupt):
        inst._safe_terminate_process(proc, signal.SIGTERM)


def test_safe_terminate_unhandled_exception_logged_and_swallowed(monkeypatch):
    inst = _make_inst()

    def fake_getpgid(pid):
        raise ValueError("unexpected")

    monkeypatch.setattr(os, "getpgid", fake_getpgid)

    class P:
        pid = 1111

    proc = P()
    # Should swallow the generic exception and not raise
    assert inst._safe_terminate_process(proc, signal.SIGTERM) is None
