# file: aider/io.py:1088-1103
# asked: {"lines": [1091, 1092, 1093, 1094, 1096, 1097, 1098, 1099, 1100, 1102, 1103], "branches": [[1090, 1091], [1091, 1092], [1091, 1102], [1096, 1097], [1096, 1103]]}
# gained: {"lines": [1091, 1092, 1093, 1094, 1096, 1097, 1098, 1099, 1100, 1102, 1103], "branches": [[1090, 1091], [1091, 1092], [1091, 1102], [1096, 1097], [1096, 1103]]}

import builtins
from types import SimpleNamespace
import pytest

import importlib
import aider.io as io_module
from aider.io import InputOutput


def test_ring_bell_prints_bell_and_clears_flag(capsys):
    io = InputOutput()
    io.bell_on_next_input = True
    io.notifications = True
    io.notifications_command = ""  # falsy -> should print bell
    # Ensure tool_warning won't interfere if called unexpectedly
    called = []
    io.tool_warning = lambda msg: called.append(msg)

    io.ring_bell()

    captured = capsys.readouterr()
    # Bell character is '\a'
    assert "\a" in captured.out
    assert io.bell_on_next_input is False
    assert called == []


def test_ring_bell_runs_command_no_warning(monkeypatch):
    io = InputOutput()
    io.bell_on_next_input = True
    io.notifications = True
    io.notifications_command = "notify-cmd"

    # Simulate subprocess.run returning success with no stderr
    fake_result = SimpleNamespace(returncode=0, stderr=b"")
    def fake_run(cmd, shell, capture_output):
        assert cmd == "notify-cmd"
        assert shell is True
        assert capture_output is True
        return fake_result

    monkeypatch.setattr(io_module.subprocess, "run", fake_run)

    warnings = []
    io.tool_warning = lambda msg: warnings.append(msg)

    io.ring_bell()

    assert warnings == []
    assert io.bell_on_next_input is False


def test_ring_bell_command_nonzero_with_stderr_triggers_warning(monkeypatch):
    io = InputOutput()
    io.bell_on_next_input = True
    io.notifications = True
    io.notifications_command = "notify-cmd"

    fake_result = SimpleNamespace(returncode=2, stderr=b"some error bytes")
    def fake_run(cmd, shell, capture_output):
        return fake_result

    monkeypatch.setattr(io_module.subprocess, "run", fake_run)

    warnings = []
    io.tool_warning = lambda msg: warnings.append(msg)

    io.ring_bell()

    assert len(warnings) == 1
    assert "Failed to run notifications command" in warnings[0]
    # Ensure stderr was decoded and included
    assert "some error bytes" in warnings[0]
    assert io.bell_on_next_input is False


def test_ring_bell_subprocess_raises_triggers_warning(monkeypatch):
    io = InputOutput()
    io.bell_on_next_input = True
    io.notifications = True
    io.notifications_command = "notify-cmd"

    def fake_run_raises(cmd, shell, capture_output):
        raise RuntimeError("boom")

    monkeypatch.setattr(io_module.subprocess, "run", fake_run_raises)

    warnings = []
    io.tool_warning = lambda msg: warnings.append(msg)

    io.ring_bell()

    assert len(warnings) == 1
    assert "Failed to run notifications command" in warnings[0]
    assert "boom" in warnings[0]
    assert io.bell_on_next_input is False
