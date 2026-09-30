# file: sweagent/agent/models.py:346-350
# asked: {"lines": [348, 349, 350], "branches": [[348, 349], [348, 350]]}
# gained: {"lines": [348, 349, 350], "branches": [[348, 349], [348, 350]]}

import types
from pathlib import Path

import pytest

from sweagent.agent import models


class _DummyConfig:
    pass


class _DummyTools:
    def __init__(self, commands=None):
        self.commands = commands or []


def test_save_readline_history_no_readline(monkeypatch):
    """
    When the module-level `readline` is None, _save_readline_history should
    return early and not attempt to call write_history_file.
    """
    # Prevent _load_readline_history from doing anything during init
    monkeypatch.setattr(models.HumanModel, "_load_readline_history", lambda self: None)

    # Ensure module readline is None for this branch
    monkeypatch.setattr(models, "readline", None)

    hm = models.HumanModel(config=_DummyConfig(), tools=_DummyTools())

    # calling should be a no-op and not raise
    result = hm._save_readline_history()
    assert result is None

    # verify the attribute is still present on instance and path looks like a Path
    assert hasattr(hm, "_readline_histfile")
    assert isinstance(hm._readline_histfile, Path)


def test_save_readline_history_writes_file(monkeypatch):
    """
    When module-level `readline` is present, _save_readline_history should call
    readline.write_history_file with the model's _readline_histfile path.
    """
    # Prevent _load_readline_history from doing anything during init
    monkeypatch.setattr(models.HumanModel, "_load_readline_history", lambda self: None)

    calls = []

    class FakeReadline:
        def write_history_file(self, path):
            # record the call but do NOT touch filesystem
            calls.append(path)
            # also assert it's a Path-like object
            assert isinstance(path, (str, Path))

    fake = FakeReadline()

    # Set module readline to our fake
    monkeypatch.setattr(models, "readline", fake)

    hm = models.HumanModel(config=_DummyConfig(), tools=_DummyTools())

    # perform the save
    hm._save_readline_history()

    # Ensure our fake was called exactly once with the model's histfile
    assert len(calls) == 1
    assert calls[0] == hm._readline_histfile
