import builtins
import platform
import pytest

import aider.utils as utils


class FakeIO:
    def __init__(self, confirm_result=True):
        self.tool_output_calls = []
        self.tool_warning_calls = []
        self.tool_error_calls = []
        self.confirm_calls = []
        self._confirm_result = confirm_result

    def tool_output(self, msg):
        self.tool_output_calls.append(msg)

    def tool_warning(self, msg):
        self.tool_warning_calls.append(msg)

    def tool_error(self, msg):
        self.tool_error_calls.append(msg)

    def confirm_ask(self, prompt, default="y", subject=None):
        self.confirm_calls.append((prompt, default, subject))
        return self._confirm_result


def test_self_update_windows_round_031(monkeypatch, capsys):
    """When self_update True and platform is Windows, function should call tool_output and print the command, then return None."""
    io = FakeIO()
    monkeypatch.setattr(utils, "get_pip_install", lambda cmd: ["pip", "install", "mypkg"])
    monkeypatch.setattr(utils, "printable_shell_command", lambda cmd: "pip install mypkg")
    # Patch platform.system to simulate Windows
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    ret = utils.check_pip_install_extra(io=io, module=None, prompt=None, pip_install_cmd=None, self_update=True)

    out = capsys.readouterr().out
    assert ret is None
    assert io.tool_output_calls == ["Run this command to update:"]
    # printed command should appear in stdout
    assert "pip install mypkg" in out


def test_confirm_decline_round_031(monkeypatch):
    """When user declines confirm_ask after a prompt, tool_warning should be called and function returns None."""
    io = FakeIO(confirm_result=False)
    monkeypatch.setattr(utils, "get_pip_install", lambda cmd: ["pip", "install", "mypkg"])
    monkeypatch.setattr(utils, "printable_shell_command", lambda cmd: "pip install mypkg")

    ret = utils.check_pip_install_extra(io=io, module=None, prompt="Please install", pip_install_cmd=None, self_update=False)

    assert ret is None
    assert io.tool_warning_calls == ["Please install"]
    # confirm_ask should have been called with expected signature and subject
    assert io.confirm_calls == [("Run pip install?", "y", "pip install mypkg")]


def test_install_success_then_import_succeeds_round_031(monkeypatch):
    """If initial import fails, install succeeds, and subsequent import succeeds, function returns True."""
    io = FakeIO(confirm_result=True)

    # make get_pip_install deterministic
    monkeypatch.setattr(utils, "get_pip_install", lambda cmd: ["pip", "install", "pkg"])
    monkeypatch.setattr(utils, "printable_shell_command", lambda cmd: "pip install pkg")
    # run_install reports success
    monkeypatch.setattr(utils, "run_install", lambda cmd: (True, "ok"))

    real_import = builtins.__import__

    # fake_import: first attempt to import 'pkg' raises ImportError, subsequent attempts delegate to real import
    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pkg" and getattr(fake_import, "calls", 0) == 0:
            fake_import.calls = getattr(fake_import, "calls", 0) + 1
            raise ImportError("notfound")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    try:
        result = utils.check_pip_install_extra(io=io, module="pkg", prompt=None, pip_install_cmd=None, self_update=False)
    finally:
        # ensure import is restored by monkeypatch fixture automatically; this finally is just to be explicit in logic
        pass

    assert result is True
    # no error messages should be emitted
    assert io.tool_error_calls == []


def test_install_success_but_import_fails_round_031(monkeypatch, capsys):
    """If install reports success but import still fails, tool_error should be called for the exception and for install output, and final failure printed."""
    io = FakeIO(confirm_result=True)

    monkeypatch.setattr(utils, "get_pip_install", lambda cmd: ["pip", "install", "pkg"])
    monkeypatch.setattr(utils, "printable_shell_command", lambda cmd: "pip install pkg")
    # run_install reports success but import will fail
    monkeypatch.setattr(utils, "run_install", lambda cmd: (True, "ok-output"))

    # make __import__ always fail for this module
    def always_fail_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pkg":
            raise ImportError("still not available")
        return builtins.__import__(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", always_fail_import)

    ret = utils.check_pip_install_extra(io=io, module="pkg", prompt=None, pip_install_cmd=None, self_update=False)

    captured = capsys.readouterr()
    # function doesn't return True in this path
    assert ret is None
    # first tool_error call should be the exception message, second should be the install output
    assert any("still not available" in e for e in io.tool_error_calls)
    assert any("ok-output" in e for e in io.tool_error_calls)
    # printed failure message should appear
    assert "Install failed, try running this command manually:" in captured.out
    assert "pip install pkg" in captured.out


def test_install_failure_round_031(monkeypatch, capsys):
    """If run_install reports failure, tool_error should be called with the output and failure printed."""
    io = FakeIO(confirm_result=True)
    monkeypatch.setattr(utils, "get_pip_install", lambda cmd: ["pip", "install", "pkg"])
    monkeypatch.setattr(utils, "printable_shell_command", lambda cmd: "pip install pkg")
    monkeypatch.setattr(utils, "run_install", lambda cmd: (False, "broken-output"))

    ret = utils.check_pip_install_extra(io=io, module=None, prompt=None, pip_install_cmd=None, self_update=False)
    captured = capsys.readouterr()

    assert ret is None
    assert io.tool_error_calls == ["broken-output"]
    assert "Install failed, try running this command manually:" in captured.out
    assert "pip install pkg" in captured.out
