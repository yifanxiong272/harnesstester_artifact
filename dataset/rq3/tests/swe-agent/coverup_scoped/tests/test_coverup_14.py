# file: sweagent/agent/action_sampler.py:211-226
# asked: {"lines": [213, 214, 215, 216, 217, 218, 219, 220, 221, 223, 224, 226], "branches": [[216, 217], [216, 223], [218, 216], [218, 219], [223, 224], [223, 226]]}
# gained: {"lines": [213, 214, 215, 216, 217, 218, 219, 220, 221, 223, 224, 226], "branches": [[216, 217], [216, 223], [218, 216], [218, 219], [223, 224], [223, 226]]}

import pytest
from typing import Any, Tuple

from sweagent.agent.action_sampler import BinaryTrajectoryComparison


class DummyTools:
    def __init__(self, mapping):
        # mapping: function or dict to derive (thought, action) from completion dict
        self._mapping = mapping

    def parse_actions(self, pc: dict[str, Any]) -> Tuple[str, str]:
        if callable(self._mapping):
            return self._mapping(pc)
        # mapping is dict keyed by id
        return self._mapping[pc.get("id")]


class DummyLogger:
    def __init__(self):
        self.calls = []

    def debug(self, *args, **kwargs):
        # store raw args to assert they were passed through
        self.calls.append((args, kwargs))


def make_instance(tools):
    # Avoid running BinaryTrajectoryComparison.__init__ to not depend on other internals.
    inst = object.__new__(BinaryTrajectoryComparison)
    inst._tools = tools
    inst._logger = DummyLogger()
    # config not used by filter_duplicates but set for completeness
    inst.config = None
    return inst


def test_filter_duplicates_removes_duplicates():
    # Prepare completions where actions duplicate: ids 1 and 2 share action a1; ids 3 and 4 share action a2.
    completions = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]

    def mapping(pc):
        i = pc["id"]
        if i in (1, 2):
            return (f"thought{i}", "a1")
        else:
            return (f"thought{i}", "a2")

    tools = DummyTools(mapping)
    inst = make_instance(tools)

    filtered = inst.filter_duplicates(completions)

    # Expect first occurrences of each action: id 1 (a1) and id 3 (a2)
    assert filtered == [completions[0], completions[2]]

    # Logger.debug should have been called once with the format string and counts
    assert len(inst._logger.calls) == 1
    args, kwargs = inst._logger.calls[0]
    # The code calls: self._logger.debug("Filtering duplicates: %d -> %d", len(completions), len(filtered_completions))
    assert args[0] == "Filtering duplicates: %d -> %d"
    assert args[1] == len(completions)
    assert args[2] == len(filtered)


def test_filter_duplicates_keeps_all_when_unique():
    # Prepare completions with unique actions
    completions = [{"id": 10}, {"id": 20}, {"id": 30}]

    mapping = {
        10: ("t10", "a10"),
        20: ("t20", "a20"),
        30: ("t30", "a30"),
    }

    tools = DummyTools(mapping)
    inst = make_instance(tools)

    filtered = inst.filter_duplicates(completions)

    # When no duplicates, filtered should equal original completions and no debug logging
    assert filtered == completions
    assert inst._logger.calls == []
