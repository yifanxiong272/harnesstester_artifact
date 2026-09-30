# file: sweagent/agent/reviewer.py:548-555
# asked: {"lines": [550, 551, 552, 553, 554, 555], "branches": [[550, 551], [550, 552], [552, 553], [552, 554]]}
# gained: {"lines": [550, 551, 552, 553, 554, 555], "branches": [[550, 551], [550, 552], [552, 553], [552, 554]]}

import pytest
from sweagent.agent.reviewer import ChooserRetryLoop


class _DummyChooser:
    def __init__(self, return_idx=7):
        self.calls = []
        self._return_idx = return_idx

    def choose(self, problem_statement, submissions):
        # record call and return a simple object with chosen_idx attribute
        self.calls.append((problem_statement, submissions))
        return type("ChooserOutput", (), {"chosen_idx": self._return_idx})()


class _DummyProblemStatement:
    def __init__(self, text="problem-statement"):
        self._text = text

    def get_problem_statement(self):
        return self._text


def test_get_best_returns_cached_when_chooser_output_present():
    # Create instance without calling __init__ to avoid heavy dependencies
    loop = object.__new__(ChooserRetryLoop)
    # Set chooser output already present
    loop._chooser_output = type("Out", (), {"chosen_idx": 42})()
    # Even if other attributes missing, get_best should return cached chosen_idx
    assert loop.get_best() == 42


def test_get_best_returns_none_when_no_submissions_and_no_cached_output():
    loop = object.__new__(ChooserRetryLoop)
    loop._chooser_output = None
    loop._submissions = []
    # Should return None when there are no submissions
    assert loop.get_best() is None


def test_get_best_calls_chooser_and_caches_result(monkeypatch):
    loop = object.__new__(ChooserRetryLoop)
    loop._chooser_output = None
    # non-empty submissions to force chooser.choose to be called
    loop._submissions = ["submission1", "submission2"]
    dummy_chooser = _DummyChooser(return_idx=99)
    loop._chooser = dummy_chooser
    loop._problem_statement = _DummyProblemStatement(text="PS-1")

    # First call should invoke chooser.choose and return its chosen_idx
    result = loop.get_best()
    assert result == 99
    assert dummy_chooser.calls == [("PS-1", loop._submissions)]

    # Second call should return cached value and not call chooser.choose again
    result2 = loop.get_best()
    assert result2 == 99
    assert dummy_chooser.calls == [("PS-1", loop._submissions)]
