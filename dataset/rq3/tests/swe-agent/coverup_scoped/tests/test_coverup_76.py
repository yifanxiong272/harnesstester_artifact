# file: sweagent/agent/reviewer.py:513-515
# asked: {"lines": [515], "branches": []}
# gained: {"lines": [515], "branches": []}

import importlib
import types

import pytest


def test_review_model_stats_returns_instance(monkeypatch):
    # Import the module under test
    reviewer = importlib.import_module("sweagent.agent.reviewer")

    # Replace Chooser with a lightweight dummy to avoid side effects during __init__
    class DummyChooser:
        def __init__(self, cfg):
            self.cfg = cfg

    monkeypatch.setattr(reviewer, "Chooser", DummyChooser, raising=True)

    # Replace get_logger with a no-op logger factory to avoid real logging side effects
    class DummyLogger:
        def debug(self, *a, **k):  # pragma: no cover - trivial pass
            pass

        def info(self, *a, **k):  # pragma: no cover - trivial pass
            pass

    monkeypatch.setattr(reviewer, "get_logger", lambda *a, **k: DummyLogger(), raising=True)

    # Minimal config and problem_statement objects required by the constructor
    class DummyConfig:
        def __init__(self):
            self.chooser = "dummy"

    class DummyProblemStatement:
        pass

    # Construct the object and access the property that should execute the target line
    loop = reviewer.ChooserRetryLoop(DummyConfig(), DummyProblemStatement())
    stats1 = loop.review_model_stats
    stats2 = loop.review_model_stats

    # Assertions: ensure an InstanceStats object is returned and a new instance is created each access
    assert isinstance(stats1, reviewer.InstanceStats)
    assert isinstance(stats2, reviewer.InstanceStats)
    assert stats1 is not stats2
