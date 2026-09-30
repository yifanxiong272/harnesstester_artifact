# file: sweagent/agent/action_sampler.py:211-226
# asked: {"lines": [213, 214, 215, 216, 217, 218, 219, 220, 221, 223, 224, 226], "branches": [[216, 217], [216, 223], [218, 216], [218, 219], [223, 224], [223, 226]]}
# gained: {"lines": [213, 214, 215, 216, 217, 218, 219, 220, 221, 223, 224, 226], "branches": [[216, 217], [216, 223], [218, 216], [218, 219], [223, 224], [223, 226]]}

import pytest
from sweagent.agent.action_sampler import BinaryTrajectoryComparison


class DummyTools:
    def __init__(self, parser):
        self.parse_actions = parser


class DummyLogger:
    def __init__(self):
        self.calls = []

    def debug(self, *args, **kwargs):
        self.calls.append((args, kwargs))


def make_instance(parse_fn):
    # Create instance without calling __init__
    inst = object.__new__(BinaryTrajectoryComparison)
    inst._tools = DummyTools(parse_fn)
    inst._logger = DummyLogger()
    return inst


def test_filter_duplicates_removes_duplicates_and_logs():
    # parse_actions returns (thought, action) using fields from the dict
    def parse_fn(pc):
        return pc.get("thought", ""), pc["action"]

    inst = make_instance(parse_fn)

    completions = [
        {"action": "jump", "thought": "first", "meta": 1},
        {"action": "run", "thought": "second", "meta": 2},
        {"action": "jump", "thought": "third", "meta": 3},  # duplicate action "jump"
    ]

    filtered = inst.filter_duplicates(completions)

    # Should keep first "jump" and "run" only (2 items)
    assert len(filtered) == 2
    assert filtered[0] is completions[0]
    assert filtered[1] is completions[1]

    # Logger debug should have been called once with expected counts
    assert len(inst._logger.calls) == 1
    args, kwargs = inst._logger.calls[0]
    # First positional arg is the format string
    assert args[0] == "Filtering duplicates: %d -> %d"
    # Next positional args are the two numbers
    assert args[1] == len(completions)
    assert args[2] == len(filtered)
    assert kwargs == {}


def test_filter_duplicates_no_duplicates_no_log():
    def parse_fn(pc):
        return pc.get("thought", ""), pc["action"]

    inst = make_instance(parse_fn)

    completions = [
        {"action": "jump", "thought": "first"},
        {"action": "run", "thought": "second"},
        {"action": "slide", "thought": "third"},
    ]

    filtered = inst.filter_duplicates(completions)

    # No duplicates: filtered should be identical to input (same objects, same order)
    assert filtered == completions
    assert filtered is not None
    assert len(filtered) == 3

    # Logger debug should not have been called
    assert inst._logger.calls == []
