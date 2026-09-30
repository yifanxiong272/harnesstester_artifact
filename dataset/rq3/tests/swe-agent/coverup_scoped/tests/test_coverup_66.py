# file: sweagent/agent/models.py:291-305
# asked: {"lines": [297, 305], "branches": []}
# gained: {"lines": [297, 305], "branches": []}

import pytest

from sweagent.agent.models import AbstractModel, InstanceStats


class DummyModel(AbstractModel):
    def __init__(self, config=None, tools=None):
        # call parent init (it only sets type annotations but is safe to call)
        super().__init__(config, tools)
        # start with non-zero stats so reset_stats actually changes something
        self.stats = InstanceStats(instance_cost=5.5, tokens_sent=10, tokens_received=20, api_calls=1)

    def query(self, history, action_prompt="> ") -> dict:
        return {"history": history, "prompt": action_prompt}


def test_reset_stats_replaces_existing_stats():
    m = DummyModel()
    # precondition: stats had non-default values
    assert isinstance(m.stats, InstanceStats)
    assert m.stats.instance_cost == 5.5
    assert m.stats.tokens_sent == 10
    assert m.stats.tokens_received == 20
    assert m.stats.api_calls == 1

    # exercise the reset_stats line
    m.reset_stats()

    # postconditions: stats is a fresh InstanceStats with default/zeroed fields
    assert isinstance(m.stats, InstanceStats)
    assert m.stats.instance_cost == 0
    assert m.stats.tokens_sent == 0
    assert m.stats.tokens_received == 0
    assert m.stats.api_calls == 0


def test_instance_cost_limit_property_returns_zero():
    m = DummyModel()
    # access the property to execute the return 0 line
    limit = m.instance_cost_limit
    # Accept either int or float 0, and ensure value is zero
    assert limit == 0
    assert isinstance(limit, (int, float))
