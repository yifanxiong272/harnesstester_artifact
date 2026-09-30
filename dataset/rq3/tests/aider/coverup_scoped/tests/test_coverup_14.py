# file: aider/utils.py:295-332
# asked: {"lines": [300, 301, 303, 305, 306, 308, 309, 310, 311, 312, 314, 315, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 328, 330, 331, 332], "branches": [[296, 303], [305, 306], [305, 308], [308, 309], [308, 314], [314, 315], [314, 317], [318, 319], [318, 328], [319, 320], [319, 321]]}
# gained: {"lines": [300, 301, 303, 305, 306, 308, 309, 310, 311, 312, 314, 315, 317, 318, 319, 321, 322, 324, 325, 326, 328, 330, 331, 332], "branches": [[305, 306], [308, 309], [308, 314], [314, 315], [314, 317], [318, 319], [319, 321]]}

import builtins
import importlib
import types
import pytest

import aider.utils as utils
from aider.utils import check_pip_install_extra


class DummyIO:
    def __init__(self, confirm_response=True):
        self.tool_warning_messages = []
        self.tool_output_messages = []
        self.tool_error_messages = []
        self.confirm_response = confirm_response
        self.confirm_called = False
        self.last_prompt = None
        self.last_default = None
        self.last_subject = None

    def tool_warning(self, msg):
        self.tool_warning_messages.append(msg)

    def tool_output(self, msg):
        self.tool_output_messages.append(msg)

    def tool_error(self, msg):
        self.tool_error_messages.append(msg)

    def confirm_ask(self, prompt, default="y", subject=None):
        self.confirm_called = True
        self.last_prompt = prompt
        self.last_default = default
        self.last_subject = subject
        return self.confirm_response


def test_self_update_on_windows_prints_command_and_warns(monkeypatch, capsys):
    # Arrange
    io = DummyIO(confirm_response=True)
    fake_module = "nonexistent_module_self_update"
    # make sure initial import fails
    # patch get_pip_install and printable_shell_command
    monkeypatch.setattr(utils, "get_pip_install", lambda pip_install_cmd: ["pip", "install", "pkg"])
    monkeypatch.setattr(utils, "printable_shell_command", lambda cmd: "pip install pkg")
    # force Windows platform for the self_update branch
    monkeypatch.setattr(utils.platform, "system", lambda: "Windows")

    # Act
    result = check_pip_install_extra(io, fake_module, "Please install this", pip_install_cmd=None, self_update=True)

    # Assert
    # function returns None for self_update on Windows
    assert result is None
    # tool_warning called with the prompt
    assert io.tool_warning_messages == ["Please install this"]
    # tool_output called to show update instruction
    assert io.tool_output_messages == ["Run this command to update:"]
    # printable command printed to stdout (there is a preceding blank line)
    captured = capsys.readouterr()
    assert "pip install pkg" in captured.out


def test_confirm_declined_returns_without_install(monkeypatch):
    # Arrange
    io = DummyIO(confirm_response=False)
    fake_module = "nonexistent_module_confirm_decline"
    monkeypatch.setattr(utils, "get_pip_install", lambda pip_install_cmd: ["pip", "install", "pkg2"])
    monkeypatch.setattr(utils, "printable_shell_command", lambda cmd: "pip install pkg2")
    # Act
    result = check_pip_install_extra(io, fake_module, "Please install pkg2", pip_install_cmd=None, self_update=False)
    # Assert
    assert result is None
    assert io.tool_warning_messages == ["Please install pkg2"]
    # confirm_ask was invoked and returned False
    assert io.confirm_called
    assert io.last_prompt == "Run pip install?"
    assert io.last_default == "y"
    assert io.last_subject == "pip install pkg2"


def test_install_succeeds_but_module_still_missing_reports_errors_and_prints_manual(monkeypatch, capsys):
    # Arrange
    io = DummyIO(confirm_response=True)
    fake_module = "nonexistent_module_after_install"
    # get_pip_install returns a cmd object that printable_shell_command can render
    monkeypatch.setattr(utils, "get_pip_install", lambda pip_install_cmd: ["pip", "install", "somepkg"])
    monkeypatch.setattr(utils, "printable_shell_command", lambda cmd: "pip install somepkg")
    # confirm -> yes
    # simulate run_install success but import of module still fails
    monkeypatch.setattr(utils, "run_install", lambda cmd: (True, "installation succeeded output"))
    # Act
    result = check_pip_install_extra(io, fake_module, "Install somepkg?", pip_install_cmd=None, self_update=False)
    # Assert
    # When run_install returned success but import still fails, function should not return True
    assert result is None
    # tool_error should have been called first with the import error, then with the run_install output
    assert len(io.tool_error_messages) >= 1
    # First error message should indicate missing module (ImportError message)
    assert any(fake_module in msg or "No module named" in msg for msg in io.tool_error_messages)
    # The run_install output should also have been reported as an error (one of the messages)
    assert "installation succeeded output" in io.tool_error_messages
    # And the manual install guidance should be printed to stdout
    captured = capsys.readouterr()
    assert "Install failed, try running this command manually:" in captured.out
    assert "pip install somepkg" in captured.out
