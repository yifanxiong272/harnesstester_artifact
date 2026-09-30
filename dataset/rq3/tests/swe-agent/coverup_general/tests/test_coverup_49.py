# file: sweagent/agent/models.py:352-362
# asked: {"lines": [355, 356, 357, 358, 359, 360, 361, 362], "branches": [[357, 358], [357, 360], [360, 0], [360, 361]]}
# gained: {"lines": [355, 356, 357, 358, 359, 360, 361, 362], "branches": [[357, 358], [357, 360], [360, 0], [360, 361]]}

import pytest
from types import SimpleNamespace

from sweagent.agent.models import HumanModel
from sweagent.exceptions import InstanceCostLimitExceededError, TotalCostLimitExceededError


class MinimalHuman(HumanModel):
    """Minimal subclass that avoids running HumanModel.__init__ and lets us set config and stats directly."""
    def __init__(self, *, instance_cost: float, api_calls: int, cost_per_call: float,
                 per_instance_cost_limit: float, total_cost_limit: float):
        # do not call super().__init__; just provide the attributes _update_stats needs
        self.config = SimpleNamespace(
            cost_per_call=cost_per_call,
            per_instance_cost_limit=per_instance_cost_limit,
            total_cost_limit=total_cost_limit,
        )
        self.stats = SimpleNamespace(
            instance_cost=instance_cost,
            api_calls=api_calls,
        )


def test_update_stats_no_exception():
    # Arrange: ensure new instance_cost remains below both per-instance and total limits
    m = MinimalHuman(instance_cost=0.0, api_calls=0, cost_per_call=1.5,
                     per_instance_cost_limit=10.0, total_cost_limit=20.0)
    # Act
    m._update_stats()
    # Assert: stats mutated and no exception
    assert m.stats.instance_cost == pytest.approx(1.5)
    assert m.stats.api_calls == 1


def test_update_stats_raises_instance_limit():
    # Arrange: make the per-instance limit small so adding cost_per_call exceeds it
    start_cost = 4.0
    cost_per_call = 2.5
    per_instance_limit = 6.0  # start + cost = 6.5 > 6.0 => instance limit exceeded
    total_limit = 100.0  # keep total limit high so second check doesn't trigger
    m = MinimalHuman(instance_cost=start_cost, api_calls=5, cost_per_call=cost_per_call,
                     per_instance_cost_limit=per_instance_limit, total_cost_limit=total_limit)
    # Act / Assert
    with pytest.raises(InstanceCostLimitExceededError) as excinfo:
        m._update_stats()
    # The stats should have been updated before the exception is raised
    assert m.stats.instance_cost == pytest.approx(start_cost + cost_per_call)
    assert m.stats.api_calls == 6
    # Exception message should reflect the new instance cost and the per-instance limit
    expected_msg = f"Instance cost limit exceeded: {m.stats.instance_cost} > {per_instance_limit}"
    assert expected_msg in str(excinfo.value)


def test_update_stats_raises_total_limit_but_not_instance_limit():
    # Arrange: per-instance limit high so first check passes, but total limit low so second check fails
    start_cost = 4.0
    cost_per_call = 3.0
    per_instance_limit = 10.0  # start + cost = 7.0 <= 10.0 => no instance limit error
    total_limit = 6.5  # start + cost = 7.0 > 6.5 => total limit exceeded
    m = MinimalHuman(instance_cost=start_cost, api_calls=2, cost_per_call=cost_per_call,
                     per_instance_cost_limit=per_instance_limit, total_cost_limit=total_limit)
    # Act / Assert
    with pytest.raises(TotalCostLimitExceededError) as excinfo:
        m._update_stats()
    # Stats updated before raising
    assert m.stats.instance_cost == pytest.approx(start_cost + cost_per_call)
    assert m.stats.api_calls == 3
    expected_msg = f"Total cost limit exceeded: {m.stats.instance_cost} > {total_limit}"
    assert expected_msg in str(excinfo.value)
