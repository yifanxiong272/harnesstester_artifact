# file: aider/run_cmd.py:89-132
# asked: {"lines": [97, 98, 100, 102, 103, 104, 106, 108, 109, 110, 112, 114, 115, 116, 119, 120, 121, 124, 127, 128, 130, 131, 132], "branches": [[97, 98], [97, 100], [109, 110], [109, 112], [112, 114], [112, 119], [114, 115], [114, 116], [119, 120], [119, 121]]}
# gained: {"lines": [97, 98, 100, 102, 103, 104, 106, 108, 109, 110, 112, 114, 115, 116, 119, 120, 121, 124, 127, 128, 130, 131, 132], "branches": [[97, 98], [109, 110], [112, 114], [112, 119], [114, 115], [119, 120]]}

import os
import pexpect
import pytest

from aider.run_cmd import run_cmd_pexpect


def test_run_cmd_pexpect_with_shell_verbose(monkeypatch, capsys, tmp_path):
    # Arrange: set SHELL to a fake path and make os.path.exists return True for it
    shell = "/fake/shell"
    monkeypatch.setenv("SHELL", shell)

    original_exists = os.path.exists

    def exists_mock(path):
        # report that the configured SHELL exists, defer to real for others
        if path == shell:
            return True
        return original_exists(path)

    monkeypatch.setattr(os.path, "exists", exists_mock)

    calls = []

    class MockChild:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.exitstatus = None

        def interact(self, output_filter=None):
            # simulate the shell producing bytes which output_callback will write
            if output_filter is not None:
                output_filter(b"hello\n")

        def close(self):
            # simulate an exit status
            self.exitstatus = 0

    def spawn_mock(spawn_arg, *args, **kwargs):
        # verify the spawn is called with shell as the first arg and expected args kw
        calls.append({"spawn_arg": spawn_arg, "args": args, "kwargs": kwargs})
        # return a mock child
        return MockChild(spawn_arg, *args, **kwargs)

    monkeypatch.setattr(pexpect, "spawn", spawn_mock)

    # Act
    status, output = run_cmd_pexpect("echo hi", verbose=True, cwd=str(tmp_path))

    # Assert: correct return values and printed verbose messages
    assert status == 0
    assert output == "hello\n"

    captured = capsys.readouterr()
    assert "Using run_cmd_pexpect: echo hi" in captured.out
    assert f"With shell: {shell}" in captured.out
    assert f"Running pexpect.spawn with shell: {shell}" in captured.out

    # Ensure spawn was called and with correct parameters (shell + args list)
    assert calls, "pexpect.spawn was not called"
    call = calls[0]
    assert call["spawn_arg"] == shell
    # kwargs should include encoding and cwd
    assert call["kwargs"].get("encoding") == "utf-8"
    assert call["kwargs"].get("cwd") == str(tmp_path)


def test_run_cmd_pexpect_without_shell(monkeypatch, capsys, tmp_path):
    # Arrange: set SHELL to a non-existing path and make os.path.exists return False for it
    shell = "/nonexistent/shell"
    monkeypatch.setenv("SHELL", shell)

    original_exists = os.path.exists

    def exists_mock(path):
        # report that the configured SHELL does NOT exist, defer to real for others
        if path == shell:
            return False
        return original_exists(path)

    monkeypatch.setattr(os.path, "exists", exists_mock)

    calls = []

    class MockChildNoShell:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.exitstatus = None

        def interact(self, output_filter=None):
            if output_filter is not None:
                output_filter(b"no-shell\n")

        def close(self):
            self.exitstatus = 5

    def spawn_mock(cmd_arg, *args, **kwargs):
        calls.append({"spawn_arg": cmd_arg, "args": args, "kwargs": kwargs})
        return MockChildNoShell(cmd_arg, *args, **kwargs)

    monkeypatch.setattr(pexpect, "spawn", spawn_mock)

    # Act
    status, output = run_cmd_pexpect("ls -la", verbose=True, cwd=str(tmp_path))

    # Assert
    assert status == 5
    assert output == "no-shell\n"

    captured = capsys.readouterr()
    assert "Using run_cmd_pexpect: ls -la" in captured.out
    assert f"With shell: {shell}" in captured.out
    assert "Running pexpect.spawn without shell." in captured.out

    # Ensure spawn was called with the command directly
    assert calls and calls[0]["spawn_arg"] == "ls -la"
    assert calls[0]["kwargs"].get("encoding") == "utf-8"
    assert calls[0]["kwargs"].get("cwd") == str(tmp_path)


def test_run_cmd_pexpect_exception_handling(monkeypatch):
    # Arrange: ensure SHELL exists so it attempts to spawn with shell, but make spawn raise ExceptionPexpect
    shell = "/some/shell"
    monkeypatch.setenv("SHELL", shell)
    monkeypatch.setattr(os.path, "exists", lambda path: True if path == shell else False)

    def spawn_raising(*args, **kwargs):
        raise pexpect.ExceptionPexpect("spawn failed")

    monkeypatch.setattr(pexpect, "spawn", spawn_raising)

    # Act
    status, message = run_cmd_pexpect("will fail", verbose=True, cwd=None)

    # Assert: should return error status and message containing the exception text and command
    assert status == 1
    assert "Error running command will fail: spawn failed" in message
