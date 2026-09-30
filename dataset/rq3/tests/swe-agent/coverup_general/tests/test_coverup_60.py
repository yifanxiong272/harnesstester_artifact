# file: sweagent/agent/action_sampler.py:242-248
# asked: {"lines": [243, 244, 245, 246, 247, 248], "branches": [[244, 245], [244, 248], [246, 244], [246, 247]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248], "branches": [[244, 245], [244, 248], [246, 244], [246, 247]]}

import pytest
from types import SimpleNamespace
from sweagent.agent.action_sampler import BinaryTrajectoryComparison

class DummyModel:
    pass

class DummyConfig:
    pass

class DummyTools:
    def parse_actions(self, completion):
        # default placeholder; tests will monkeypatch this on instance._tools
        return (None, "")

def make_btc():
    return BinaryTrajectoryComparison(config=DummyConfig(), model=DummyModel(), tools=DummyTools())

def test_contains_edits_returns_true_when_action_starts_with_keyword(monkeypatch):
    btc = make_btc()
    completions = [{"id": 1, "content": "c1"}]

    calls = []
    def fake_parse_actions(completion):
        calls.append(completion)
        return (None, "edit file: /tmp/foo")

    monkeypatch.setattr(btc._tools, "parse_actions", fake_parse_actions)

    assert btc.contains_edits(completions) is True
    # ensure parse_actions was called with our completion
    assert calls == completions

def test_contains_edits_checks_all_and_returns_false_when_no_keywords(monkeypatch):
    btc = make_btc()
    completions = [{"id": 1}, {"id": 2}, {"id": 3}]

    calls = []
    def fake_parse_actions(completion):
        calls.append(completion)
        return (None, "some_other_action_do_not_match")

    monkeypatch.setattr(btc._tools, "parse_actions", fake_parse_actions)

    assert btc.contains_edits(completions) is False
    # ensure parse_actions was called for every completion (no early return)
    assert calls == completions

def test_contains_edits_returns_true_if_any_completion_matches(monkeypatch):
    btc = make_btc()
    completions = [{"id": "first"}, {"id": "second"}]

    calls = []
    # First completion non-matching, second matching
    def fake_parse_actions(completion):
        calls.append(completion)
        if completion.get("id") == "first":
            return (None, "no_match")
        return (None, "str_replace_editor insert something")

    monkeypatch.setattr(btc._tools, "parse_actions", fake_parse_actions)

    assert btc.contains_edits(completions) is True
    # ensure parse_actions was called at least for the first and second (stops after match)
    assert calls[0] == completions[0]
    assert calls[1] == completions[1]
    # Only two calls should have been made
    assert len(calls) == 2
