# file: sweagent/agent/models.py:338-344
# asked: {"lines": [340, 341, 342, 343, 344], "branches": [[340, 341], [340, 342], [342, 0], [342, 343]]}
# gained: {"lines": [340, 341, 342, 343, 344], "branches": [[340, 341], [340, 342], [342, 343]]}

import types
from pathlib import Path

import pytest


def _make_dummy_readline():
    class DummyReadline:
        def __init__(self):
            self.called = False
            self.called_with = None

        def read_history_file(self, path):
            self.called = True
            # store as Path for easier assertions
            self.called_with = Path(path)

    return DummyReadline()


def test_load_readline_history_calls_read_history_file(monkeypatch, tmp_path):
    """
    Ensure that when readline is available and the history file exists,
    HumanModel._load_readline_history calls readline.read_history_file with the path.
    """
    # Import the module under test
    import sweagent.agent.models as models
    from sweagent.agent.models import HumanModel

    # Prepare a dummy history file at the location that HumanModel will use
    histfile = tmp_path / ".swe-agent-human-history"
    histfile.write_text("dummy history\n")

    # Monkeypatch the module-level REPO_ROOT so HumanModel.__init__ sets _readline_histfile to our tmp file
    monkeypatch.setattr(models, "REPO_ROOT", tmp_path)

    # Provide a dummy readline with a recordable read_history_file method
    dummy_readline = _make_dummy_readline()
    monkeypatch.setattr(models, "readline", dummy_readline)

    # Provide minimal config and tools (only what HumanModel.__init__ expects)
    config = types.SimpleNamespace(name="human")
    tools = types.SimpleNamespace(commands=[])

    # Instantiate; __init__ calls _load_readline_history, which should call our dummy
    hm = HumanModel(config=config, tools=tools)

    # Confirm that read_history_file was called with the expected path
    assert dummy_readline.called is True
    assert dummy_readline.called_with == histfile

    # Calling _load_readline_history again should also call read_history_file again (update)
    dummy_readline.called = False
    dummy_readline.called_with = None
    hm._load_readline_history()
    assert dummy_readline.called is True
    assert dummy_readline.called_with == histfile


def test_load_readline_history_returns_when_readline_is_none(monkeypatch, tmp_path):
    """
    Ensure that when module-level readline is None, _load_readline_history returns without error.
    """
    import sweagent.agent.models as models
    from sweagent.agent.models import HumanModel

    # Create a history file (even if present, should not be used when readline is None)
    histfile = tmp_path / ".swe-agent-human-history"
    histfile.write_text("dummy history\n")

    monkeypatch.setattr(models, "REPO_ROOT", tmp_path)

    # Set module readline to None to exercise the early-return branch
    monkeypatch.setattr(models, "readline", None)

    config = types.SimpleNamespace(name="human")
    tools = types.SimpleNamespace(commands=[])

    # Should not raise; _load_readline_history returns early
    hm = HumanModel(config=config, tools=tools)

    # To be explicit, call the method again and ensure it does nothing and raises no exceptions
    hm._load_readline_history()

    # Verify that the instance's _readline_histfile points to our tmp file
    assert hm._readline_histfile == histfile
