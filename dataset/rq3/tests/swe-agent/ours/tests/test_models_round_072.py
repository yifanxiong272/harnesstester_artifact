import pytest
from sweagent.agent import models


class DummyReadline:
    """Minimal fake readline replacement that records calls to write_history_file."""
    def __init__(self):
        self.calls = []

    def write_history_file(self, path):
        # Record the path so tests can assert the call without touching the FS
        self.calls.append(path)


def test_save_readline_history_none_round_072(monkeypatch):
    """When the module-level `readline` is None, _save_readline_history should return early and not error."""
    # Patch the symbol where the code resolves it
    monkeypatch.setattr(models, "readline", None)

    # Instantiate HumanModel without running its constructor to avoid side effects
    hm = object.__new__(models.HumanModel)
    # Provide the attribute the method will try to pass through to write_history_file
    hm._readline_histfile = "should-not-be-used"

    # Call the method under test; it should return None and not attempt to call write_history_file
    result = hm._save_readline_history()
    assert result is None
    # The module-level symbol remains None (ensures the branch was the one taken)
    assert models.readline is None


def test_save_readline_history_calls_write_round_072(monkeypatch):
    """When a readline-like object is present, _save_readline_history should call its write_history_file with the configured path."""
    dummy = DummyReadline()
    monkeypatch.setattr(models, "readline", dummy)

    hm = object.__new__(models.HumanModel)
    hm._readline_histfile = "history_file.txt"

    # Call the method under test; it should call DummyReadline.write_history_file
    result = hm._save_readline_history()
    assert result is None

    # Verify the dummy recorded exactly the expected call
    assert dummy.calls == ["history_file.txt"]
