# file: sweagent/agent/reviewer.py:500-507
# asked: {"lines": [501, 502, 503, 504, 505, 506, 507], "branches": []}
# gained: {"lines": [501, 502, 503, 504, 505, 506, 507], "branches": []}

import types
import importlib
import pytest

def test_chooser_retry_loop_init_sets_expected_attributes(monkeypatch):
    # Import the module under test
    reviewer = importlib.import_module("sweagent.agent.reviewer")

    # Create a stub Chooser that records its initialization argument
    class StubChooser:
        def __init__(self, arg):
            self.arg = arg
        def __repr__(self):
            return f"StubChooser(arg={self.arg!r})"

    # Stub logger factory to return a simple object we can inspect
    def stub_get_logger(name, emoji=None):
        return types.SimpleNamespace(name=name, emoji=emoji)

    # Patch the Chooser and get_logger in the reviewer module
    monkeypatch.setattr(reviewer, "Chooser", StubChooser)
    monkeypatch.setattr(reviewer, "get_logger", stub_get_logger, raising=False)

    # Prepare dummy inputs for the constructor
    dummy_config = types.SimpleNamespace(chooser="my-chooser-config")
    dummy_problem = types.SimpleNamespace(problem_id="p1")

    # Instantiate the class (this should execute the lines 501-507)
    loop = reviewer.ChooserRetryLoop(dummy_config, dummy_problem)

    # Assertions to verify postconditions set in __init__
    assert loop._config is dummy_config
    assert loop._problem_statement is dummy_problem
    assert isinstance(loop._chooser, StubChooser)
    assert loop._chooser.arg == "my-chooser-config"
    assert isinstance(loop._submissions, list) and loop._submissions == []
    assert loop._n_consec_exit_cost == 0
    assert hasattr(loop, "logger")
    assert loop.logger.name == "chooser_loop"
    assert loop.logger.emoji == "🔄"
    assert loop._chooser_output is None

def test_chooser_retry_loop_with_none_chooser_arg(monkeypatch):
    # Import the module under test
    reviewer = importlib.import_module("sweagent.agent.reviewer")

    # Another stub Chooser to verify it accepts None
    class StubChooserNone:
        def __init__(self, arg):
            # Accept None explicitly
            self.arg = arg

    def stub_get_logger(name, emoji=None):
        return types.SimpleNamespace(name=name, emoji=emoji)

    monkeypatch.setattr(reviewer, "Chooser", StubChooserNone)
    monkeypatch.setattr(reviewer, "get_logger", stub_get_logger, raising=False)

    dummy_config = types.SimpleNamespace(chooser=None)
    dummy_problem = types.SimpleNamespace(problem_id="p2")

    loop = reviewer.ChooserRetryLoop(dummy_config, dummy_problem)

    assert loop._config is dummy_config
    assert loop._problem_statement is dummy_problem
    assert isinstance(loop._chooser, StubChooserNone)
    assert loop._chooser.arg is None
    assert loop._submissions == []
    assert loop._n_consec_exit_cost == 0
    assert loop._chooser_output is None
