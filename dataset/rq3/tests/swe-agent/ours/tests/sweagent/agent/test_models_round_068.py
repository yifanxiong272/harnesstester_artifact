from pathlib import Path
import types
import pytest

from sweagent.agent import models


def test_humanmodel_init_round_068(monkeypatch, tmp_path):
    """Ensure HumanModel.__init__ sets logger, config, stats, multi-line command map,
    and readline history file, and calls the loader.
    """
    # Capture calls to get_logger and return a sentinel logger object
    captured = {}

    def fake_get_logger(name, emoji=None):
        captured["name"] = name
        captured["emoji"] = emoji
        return "SENTINEL_LOGGER"

    monkeypatch.setattr(models, "get_logger", fake_get_logger)

    # Patch REPO_ROOT so the derived history path is deterministic and under tmp_path
    monkeypatch.setattr(models, "REPO_ROOT", tmp_path)

    # Patch the instance method _load_readline_history so it doesn't touch the FS
    def fake_load(self):
        # mark that it was invoked during __init__
        setattr(self, "_load_called", True)

    monkeypatch.setattr(models.HumanModel, "_load_readline_history", fake_load, raising=True)

    # Create minimal command-like objects for tools.commands
    class Cmd:
        def __init__(self, name, end_name):
            self.name = name
            self.end_name = end_name

    tools = types.SimpleNamespace(commands=[Cmd("alpha", "END_ALPHA"), Cmd("beta", None), Cmd("gamma", "END_GAMMA")])

    # Use a plain object for config (type hints are not enforced at runtime here)
    config = object()

    # Instantiate - this should exercise the lines under test deterministically
    hm = models.HumanModel(config, tools)

    # Assertions (oracle): verify logger was created with expected args and assigned
    assert hm.logger == "SENTINEL_LOGGER"
    assert captured["name"] == "swea-lm"
    # The source used a unicode escape for the robot emoji; compare the actual codepoint
    assert captured["emoji"] == "\U0001f916"

    # Config should be preserved
    assert hm.config is config

    # stats should be an InstanceStats instance
    assert isinstance(hm.stats, models.InstanceStats)

    # multi_line_command_endings should include only commands with non-None end_name
    assert hm.multi_line_command_endings == {"alpha": "END_ALPHA", "gamma": "END_GAMMA"}

    # _readline_histfile should point to REPO_ROOT / ".swe-agent-human-history"
    assert hm._readline_histfile == tmp_path / ".swe-agent-human-history"

    # Our patched loader should have been called during __init__
    assert getattr(hm, "_load_called", False) is True
