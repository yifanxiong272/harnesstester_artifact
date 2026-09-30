# file: sweagent/agent/models.py:325-336
# asked: {"lines": [327, 328, 329, 332, 333, 335, 336], "branches": []}
# gained: {"lines": [327, 328, 329, 332, 333, 335, 336], "branches": []}

import builtins
from types import SimpleNamespace
from pathlib import Path

import pytest

import sweagent.agent.models as models
from sweagent.agent.models import HumanModel


def test_humanmodel_init_loads_readline_history(tmp_path, monkeypatch):
    """
    Ensure HumanModel.__init__ sets up multi_line_command_endings, points
    _readline_histfile to REPO_ROOT/.swe-agent-human-history and calls
    readline.read_history_file when the history file exists.
    """
    # Arrange: point module REPO_ROOT to a temporary directory
    monkeypatch.setattr(models, "REPO_ROOT", tmp_path)

    # Create a fake history file at the expected path
    histfile = tmp_path / ".swe-agent-human-history"
    histfile.write_text("fake-history")

    # Create a fake readline module with a spy for read_history_file
    calls = {}

    def fake_read_history_file(path):
        # record that it was called and with which path
        calls["called_with"] = path
        # simulate normal behavior: no return value
        return None

    fake_readline = SimpleNamespace(read_history_file=fake_read_history_file, write_history_file=lambda p: None)
    monkeypatch.setattr(models, "readline", fake_readline)

    # Create a fake tools object with commands; one command has an end_name
    tools = SimpleNamespace(commands=[SimpleNamespace(name="cmd1", end_name="END"), SimpleNamespace(name="cmd2", end_name=None)])

    # Act: instantiate HumanModel (this should call _load_readline_history)
    config = SimpleNamespace()  # HumanModel only stores config
    hm = HumanModel(config=config, tools=tools)

    # Assert: multi_line_command_endings contains the command with end_name
    assert hm.multi_line_command_endings == {"cmd1": "END"}
    # Assert: the _readline_histfile is the expected file under tmp_path
    assert isinstance(hm._readline_histfile, Path)
    assert hm._readline_histfile == histfile
    # Assert: our fake readline.read_history_file was called with the Path
    assert "called_with" in calls
    assert calls["called_with"] == histfile


def test_humanmodel_init_when_readline_missing(tmp_path, monkeypatch):
    """
    Ensure HumanModel.__init__ gracefully handles the case where the
    module-level 'readline' is None.
    """
    # Arrange: set module-level REPO_ROOT to tmp_path and ensure no history file exists
    monkeypatch.setattr(models, "REPO_ROOT", tmp_path)
    histfile = tmp_path / ".swe-agent-human-history"
    if histfile.exists():
        histfile.unlink()

    # Set models.readline to None to exercise that branch
    monkeypatch.setattr(models, "readline", None)

    # Create a fake tools object with no commands having end_name
    tools = SimpleNamespace(commands=[SimpleNamespace(name="a", end_name=None)])

    # Act: instantiate HumanModel (should not raise even though readline is None)
    config = SimpleNamespace()
    hm = HumanModel(config=config, tools=tools)

    # Assert: multi_line_command_endings is empty as no command had end_name
    assert hm.multi_line_command_endings == {}
    # Assert: _readline_histfile still points under our tmp_path
    assert hm._readline_histfile == histfile
