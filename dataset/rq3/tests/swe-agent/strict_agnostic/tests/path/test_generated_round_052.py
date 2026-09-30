import pytest
from types import SimpleNamespace

from sweagent.agent.reviewer import ChooserRetryLoop


def test_cached_get_best_round_052():
    """When _chooser_output is already set, get_best() should return the cached chosen_idx."""
    loop = object.__new__(ChooserRetryLoop)
    # simulate cached chooser output
    loop._chooser_output = SimpleNamespace(chosen_idx=42)
    # Call and assert deterministic result
    assert loop.get_best() == 42


def test_get_best_no_submissions_round_052():
    """When there is no cached output and submissions is empty, get_best() should return None."""
    loop = object.__new__(ChooserRetryLoop)
    loop._chooser_output = None
    loop._submissions = []
    assert loop.get_best() is None


def test_get_best_invokes_chooser_round_052():
    """When no cached output and submissions exist, get_best() must call chooser.choose(...) and cache/return its chosen_idx."""
    loop = object.__new__(ChooserRetryLoop)
    loop._chooser_output = None
    loop._submissions = ["submissionA", "submissionB"]

    # Provide a deterministic problem_statement stub and chooser stub
    loop._problem_statement = SimpleNamespace(get_problem_statement=lambda: "PROBLEM_STATEMENT")

    called = {}

    def choose_stub(problem_statement_arg, submissions_arg):
        # Record what was passed to ensure chooser is invoked with the expected inputs
        called['ps'] = problem_statement_arg
        called['subs'] = list(submissions_arg)
        return SimpleNamespace(chosen_idx=7)

    loop._chooser = SimpleNamespace(choose=choose_stub)

    result = loop.get_best()

    # The chooser should have been invoked and its result returned
    assert result == 7
    # The chooser output must be cached on the instance
    assert hasattr(loop, "_chooser_output") and loop._chooser_output.chosen_idx == 7
    # Validate that chooser received the expected arguments
    assert called['ps'] == "PROBLEM_STATEMENT"
    assert called['subs'] == ["submissionA", "submissionB"]
