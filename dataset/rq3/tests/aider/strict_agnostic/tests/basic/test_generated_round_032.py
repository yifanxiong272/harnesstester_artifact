import builtins
import types
import sys
import platform as _platform
import pytest

from types import ModuleType

import aider.utils as utils


class FakeIO:
    def __init__(self, confirm_value=True):
        self.warnings = []
        self.outputs = []
        self.errors = []
        self.confirm_value = confirm_value
        self.confirm_calls = []

    def tool_warning(self, msg):
        self.warnings.append(msg)

    def tool_output(self, msg):
        self.outputs.append(msg)

    def tool_error(self, msg):
        self.errors.append(msg)

    def confirm_ask(self, prompt, default="y", subject=None):
        # record parameters to assert deterministically
        self.confirm_calls.append((prompt, default, subject))
        return self.confirm_value


def test_check_pip_install_extra_module_available_round_032():
    # If module is importable at the start, function returns True immediately.
    io = FakeIO()
    assert utils.check_pip_install_extra(io, module="sys", prompt=False, pip_install_cmd=None) is True


def test_check_pip_install_extra_self_update_windows_round_032(monkeypatch, capsys):
    # When self_update is True and platform is Windows, the function should call
    # tool_warning (if prompt) and tool_output then print the printable_shell_command and return.
    io = FakeIO()

    # deterministic command and printable form
    monkeypatch.setattr(utils, "get_pip_install", lambda pip_install_cmd: ["pip", "install", "mypkg"])
    monkeypatch.setattr(utils, "printable_shell_command", lambda cmd: "pip install mypkg")
    monkeypatch.setattr(utils, "platform", types.SimpleNamespace(system=lambda: "Windows"))

    # prompt provided -> should call tool_warning
    ret = utils.check_pip_install_extra(io, module=None, prompt="Please confirm", pip_install_cmd=None, self_update=True)

    # function returns None (explicit return without value)
    assert ret is None
    assert io.warnings == ["Please confirm"]
    # tool_output must have been called with the update message
    assert "Run this command to update:" in io.outputs

    # printed content should include the printable shell command
    captured = capsys.readouterr()
    assert "pip install mypkg" in captured.out


def test_check_pip_install_extra_confirm_decline_round_032(monkeypatch):
    # If user declines confirm_ask the function returns without running install.
    io = FakeIO(confirm_value=False)

    called = {"run_install": False}

    def fake_run_install(cmd):
        called["run_install"] = True
        return (True, "should-not-be-called")

    monkeypatch.setattr(utils, "get_pip_install", lambda pip_install_cmd: ["pip", "install"])
    monkeypatch.setattr(utils, "printable_shell_command", lambda cmd: "pip install")
    monkeypatch.setattr(utils, "run_install", fake_run_install)

    ret = utils.check_pip_install_extra(io, module=None, prompt=False, pip_install_cmd=None, self_update=False)

    assert ret is None
    assert called["run_install"] is False
    # confirm_ask was invoked once
    assert len(io.confirm_calls) == 1
    assert io.confirm_calls[0][0] == "Run pip install?"


def test_check_pip_install_extra_success_no_module_round_032(monkeypatch):
    # When run_install indicates success and no module was requested, function returns True.
    io = FakeIO(confirm_value=True)

    monkeypatch.setattr(utils, "get_pip_install", lambda pip_install_cmd: ["pip", "install", "pkg"])
    monkeypatch.setattr(utils, "printable_shell_command", lambda cmd: "pip install pkg")
    monkeypatch.setattr(utils, "run_install", lambda cmd: (True, "ok"))

    ret = utils.check_pip_install_extra(io, module=None, prompt=False, pip_install_cmd=None, self_update=False)
    assert ret is True


def test_check_pip_install_extra_success_module_imports_after_install_round_032(monkeypatch):
    # Simulate a module that is not importable initially (so function proceeds to install),
    # but becomes importable on the second __import__ call after installation.
    io = FakeIO(confirm_value=True)

    module_name = "transient_mod_round032"

    # Ensure deterministic get_pip_install and run_install
    monkeypatch.setattr(utils, "get_pip_install", lambda pip_install_cmd: ["pip", "install", module_name])
    monkeypatch.setattr(utils, "printable_shell_command", lambda cmd: "pip install " + module_name)
    monkeypatch.setattr(utils, "run_install", lambda cmd: (True, "ok"))

    # custom import that fails once for our module, then succeeds
    original_import = builtins.__import__
    state = {"count": 0}

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == module_name:
            state["count"] += 1
            if state["count"] == 1:
                raise ModuleNotFoundError(module_name)
            # on subsequent import calls, return a simple ModuleType to simulate availability
            return ModuleType(module_name)
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    try:
        ret = utils.check_pip_install_extra(io, module=module_name, prompt=False, pip_install_cmd=None, self_update=False)
        assert ret is True
    finally:
        # monkeypatch will restore builtins.__import__ automatically when test ends,
        # but guard nonetheless if manual state change occurred
        pass


def test_check_pip_install_extra_install_success_but_module_import_fails_round_032(monkeypatch, capsys):
    # When install claims success but the requested module still cannot be imported,
    # the function should report the import error via io.tool_error and then report the
    # install output and print the failure message and printable shell command.
    io = FakeIO(confirm_value=True)

    module_name = "broken_mod_round032"

    monkeypatch.setattr(utils, "get_pip_install", lambda pip_install_cmd: ["pip", "install", module_name])
    monkeypatch.setattr(utils, "printable_shell_command", lambda cmd: "pip install " + module_name)
    monkeypatch.setattr(utils, "run_install", lambda cmd: (True, "install-succeeded-output"))

    # Make __import__ always raise for this module name
    original_import = builtins.__import__

    def always_fail_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == module_name:
            raise ModuleNotFoundError("cannot import: " + name)
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", always_fail_import)

    try:
        ret = utils.check_pip_install_extra(io, module=module_name, prompt=False, pip_install_cmd=None, self_update=False)

        # function returns None (falls through after reporting)
        assert ret is None

        # The import error should have been reported first
        assert any("cannot import" in e for e in io.errors)

        # The install output should also have been reported as an error
        assert any("install-succeeded-output" in e for e in io.errors)

        # Final printed output should include the failure message and command
        captured = capsys.readouterr()
        assert "Install failed, try running this command manually:" in captured.out
        assert "pip install " + module_name in captured.out
    finally:
        pass
