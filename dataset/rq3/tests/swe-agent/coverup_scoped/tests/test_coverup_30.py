# file: sweagent/agent/action_sampler.py:242-248
# asked: {"lines": [243, 244, 245, 246, 247, 248], "branches": [[244, 245], [244, 248], [246, 244], [246, 247]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248], "branches": [[244, 245], [244, 248], [246, 244], [246, 247]]}

import pytest
from typing import Any

from sweagent.agent.action_sampler import BinaryTrajectoryComparison


class MockTools:
    def __init__(self, actions):
        # actions is a list of action strings that parse_actions will return (in order)
        self._actions = list(actions)
        self.calls = []

    def parse_actions(self, completion: dict[str, Any]):
        # record the completion passed in and return a tuple (ignored, action)
        self.calls.append(completion)
        if not self._actions:
            # If no more predefined actions, return a non-matching action
            return None, "no_action"
        return None, self._actions.pop(0)


def make_instance_with_tools(actions):
    # Create an instance without calling __init__ to avoid needing real config/model
    inst = object.__new__(BinaryTrajectoryComparison)
    inst._tools = MockTools(actions)
    return inst


def test_contains_edits_returns_true_for_edit_keyword():
    # Single completion whose parsed action starts with "edit" should return True
    instance = make_instance_with_tools(["edit replace something"])
    completions = [{"id": 1, "text": "dummy"}]

    result = instance.contains_edits(completions)

    assert result is True
    # verify parse_actions was called exactly once with our completion
    assert instance._tools.calls == completions


def test_contains_edits_returns_true_for_str_replace_editor_variants():
    # Test both "str_replace_editor insert" and "str_replace_editor str_replace" prefixes
    instance_insert = make_instance_with_tools(["str_replace_editor insert extra"])
    instance_str_replace = make_instance_with_tools(["str_replace_editor str_replace extra"])
    completions = [{"id": "a"}]

    assert instance_insert.contains_edits(completions) is True
    assert instance_insert._tools.calls == completions

    assert instance_str_replace.contains_edits(completions) is True
    assert instance_str_replace._tools.calls == completions


def test_contains_edits_returns_false_and_parses_all_when_no_match():
    # When none of the completions produce matching actions, returns False
    actions = ["do_something", "another_action", "still_not_edit"]
    instance = make_instance_with_tools(list(actions))
    completions = [{"i": 1}, {"i": 2}, {"i": 3}]

    result = instance.contains_edits(completions)

    assert result is False
    # parse_actions should have been called for each completion
    assert instance._tools.calls == completions


def test_contains_edits_early_return_stops_parsing():
    # If a later completion matches, ensure the method returns True and stops parsing further completions
    actions = ["no_match", "str_replace_editor insert something", "should_not_be_parsed"]
    instance = make_instance_with_tools(list(actions))
    completions = [{"i": "first"}, {"i": "second"}, {"i": "third"}]

    result = instance.contains_edits(completions)

    assert result is True
    # parse_actions should have been called only for the first two completions (stops after match)
    assert instance._tools.calls == completions[:2]
