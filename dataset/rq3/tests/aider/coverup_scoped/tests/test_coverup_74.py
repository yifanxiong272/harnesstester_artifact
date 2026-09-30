# file: aider/io.py:237-372
# asked: {"lines": [275, 314, 315, 316, 354, 360, 361, 362], "branches": [[274, 275], [353, 354]]}
# gained: {"lines": [275, 314, 315, 316, 354, 360, 361, 362], "branches": [[274, 275], [353, 354]]}

import os
import pytest
from pathlib import Path

import aider.io as aio
from aider.io import InputOutput
from prompt_toolkit.enums import EditingMode


def test_notifications_uses_default_command(monkeypatch):
    # Ensure NO_COLOR doesn't interfere
    monkeypatch.delenv("NO_COLOR", raising=False)

    # Patch get_default_notification_command to return a known value
    monkeypatch.setattr(
        InputOutput, "get_default_notification_command", lambda self: "notify-default-cmd"
    )

    io = InputOutput(notifications=True, notifications_command=None, fancy_input=False)
    assert io.notifications is True
    assert io.notifications_command == "notify-default-cmd"


def test_input_history_dir_creation_permission_error(monkeypatch, tmp_path):
    # Ensure NO_COLOR doesn't interfere
    monkeypatch.delenv("NO_COLOR", raising=False)

    # Prepare a path under tmp_path
    hist_path = tmp_path / "subdir" / "history.txt"

    # Make Path.mkdir raise PermissionError to trigger the except branch
    def raise_perm(self, parents=True, exist_ok=True):
        raise PermissionError("nope")

    monkeypatch.setattr(Path, "mkdir", raise_perm, raising=True)

    # Capture tool_warning calls
    warnings = []

    def fake_tool_warning(self, message="", strip=True):
        warnings.append(message)

    monkeypatch.setattr(InputOutput, "tool_warning", fake_tool_warning, raising=True)

    io = InputOutput(input_history_file=str(hist_path), fancy_input=False)

    # After failure, input_history_file should be set to None and warning called
    assert io.input_history_file is None
    assert any("Could not create directory for input history" in w for w in warnings)


def test_prompt_session_sets_cursor_for_vi_and_success(monkeypatch):
    # Ensure NO_COLOR doesn't interfere
    monkeypatch.delenv("NO_COLOR", raising=False)

    # Make terminal capable by patching the function in the module
    monkeypatch.setattr(aio, "is_dumb_terminal", lambda: False)

    # Dummy PromptSession that captures kwargs
    captured = {}

    class DummySession:
        def __init__(self, **kwargs):
            # store kwargs so test can inspect them
            captured.update(kwargs)

    monkeypatch.setattr(aio, "PromptSession", DummySession)

    io = InputOutput(editingmode=EditingMode.VI, fancy_input=True)

    # confirm PromptSession used and cursor kw present
    assert io.prompt_session is not None
    assert "cursor" in captured
    # cursor should be ModalCursorShapeConfig instance
    from prompt_toolkit.cursor_shapes import ModalCursorShapeConfig

    assert isinstance(captured["cursor"], ModalCursorShapeConfig)


def test_prompt_session_exception_sets_console_and_reports_error(monkeypatch):
    # Ensure NO_COLOR doesn't interfere
    monkeypatch.delenv("NO_COLOR", raising=False)

    # Make terminal capable
    monkeypatch.setattr(aio, "is_dumb_terminal", lambda: False)

    # Make PromptSession raise to hit the except branch
    def raise_on_init(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(aio, "PromptSession", raise_on_init)

    errors = []

    def fake_tool_error(self, message="", strip=True):
        errors.append(message)

    monkeypatch.setattr(InputOutput, "tool_error", fake_tool_error, raising=True)

    io = InputOutput(fancy_input=True)

    # prompt_session failed to initialize
    assert io.prompt_session is None

    # console should be set to a Console instance created in except branch
    console = getattr(io, "console", None)
    assert console is not None
    assert isinstance(console, aio.Console)

    # rich.Console stores the force_terminal flag internally as _force_terminal
    # Validate that it was set to False in the except branch call
    assert getattr(console, "_force_terminal", None) is False

    # tool_error must have been called with the underlying error message
    assert any("Can't initialize prompt toolkit" in e for e in errors)
    assert any("boom" in e for e in errors)
