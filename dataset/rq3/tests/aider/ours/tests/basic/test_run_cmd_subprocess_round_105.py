import os
import types
import pytest

import aider.run_cmd as rc


class _FakeStdout:
    def __init__(self, data):
        # simulate byte/str stream read(1) returning one character at a time
        self._buf = list(data)

    def read(self, n=1):
        if not self._buf:
            return ""
        # ignore n, always return single-character chunks like the real code expects
        return self._buf.pop(0)


class FakePopen:
    def __init__(self, command, stdout, stderr, text, shell, encoding, errors, bufsize, universal_newlines, cwd):
        # store for assertions if needed
        self.command = command
        self.stdout = _FakeStdout("abc")
        self.returncode = 0

    def wait(self):
        # simulate process finishing
        return None


class RaisingPopen:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("boom")


def test_windows_powershell_round_105(monkeypatch, capsys):
    """
    Exercising branch where platform is Windows and parent process is powershell.exe.
    Ensures command gets prefixed, verbose prints occur, and output is collected.
    """
    # Arrange: deterministic environment
    monkeypatch.setenv("SHELL", "/bin/testshell")
    monkeypatch.setattr(rc.platform, "system", lambda: "Windows")
    monkeypatch.setattr(rc, "get_windows_parent_process_name", lambda: "powershell.exe")
    monkeypatch.setattr(rc.subprocess, "Popen", FakePopen)

    # Act
    code, out = rc.run_cmd_subprocess("echo hi", verbose=True, cwd=None, encoding="utf-8")

    # Assert
    captured = capsys.readouterr()
    # return code and collected output
    assert code == 0
    assert out == "abc"

    # verbose messages: initial and after powerhsell wrapping
    assert "Using run_cmd_subprocess: echo hi" in captured.out
    assert "Running command: powershell -Command echo hi" in captured.out
    # SHELL and Parent process messages should appear
    assert "SHELL: /bin/testshell" in captured.out
    assert "Parent process: powershell.exe" in captured.out
    # the streamed chunks are printed in real-time (no newline between them)
    assert "abc" in captured.out


def test_windows_non_powershell_round_105(monkeypatch, capsys):
    """
    Exercising branch where platform is Windows but parent process is not powershell.
    Command should remain unchanged and verbose prints should reflect that.
    """
    monkeypatch.setenv("SHELL", "/bin/testshell")
    monkeypatch.setattr(rc.platform, "system", lambda: "Windows")
    monkeypatch.setattr(rc, "get_windows_parent_process_name", lambda: "cmd.exe")
    monkeypatch.setattr(rc.subprocess, "Popen", FakePopen)

    code, out = rc.run_cmd_subprocess("doit", verbose=True, cwd=None, encoding="utf-8")
    captured = capsys.readouterr()

    assert code == 0
    assert out == "abc"

    # initial print uses the original command
    assert "Using run_cmd_subprocess: doit" in captured.out
    # Running command should not be wrapped with powershell
    assert "Running command: doit" in captured.out
    assert "Parent process: cmd.exe" in captured.out


def test_subprocess_constructor_raises_round_105(monkeypatch):
    """
    If subprocess.Popen raises, run_cmd_subprocess should catch and return (1, str(e)).
    This covers the exception handler path.
    """
    monkeypatch.setattr(rc.subprocess, "Popen", RaisingPopen)

    code, out = rc.run_cmd_subprocess("any", verbose=False, cwd=None, encoding="utf-8")

    assert code == 1
    # Exact message from the raised exception should be returned
    assert "boom" in out
