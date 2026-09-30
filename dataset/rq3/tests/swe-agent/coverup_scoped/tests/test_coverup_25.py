# file: sweagent/agent/models.py:352-362
# asked: {"lines": [355, 356, 357, 358, 359, 360, 361, 362], "branches": [[357, 358], [357, 360], [360, 0], [360, 361]]}
# gained: {"lines": [355, 356, 357, 358, 359, 360, 361, 362], "branches": [[357, 358], [357, 360], [360, 0], [360, 361]]}

import pytest
from types import SimpleNamespace

from sweagent.agent.models import HumanModel
from sweagent.exceptions import InstanceCostLimitExceededError, TotalCostLimitExceededError


def make_human_model_with(stats: SimpleNamespace, config: SimpleNamespace) -> HumanModel:
    """
    Construct a HumanModel-like object without calling its __init__,
    to avoid side effects (file IO, logging, etc).
    """
    hm = object.__new__(HumanModel)
    hm.stats = stats
    hm.config = config
    return hm


def test_update_stats_no_exception():
    stats = SimpleNamespace(instance_cost=0.0, api_calls=0)
    config = SimpleNamespace(cost_per_call=1.5, per_instance_cost_limit=10.0, total_cost_limit=20.0)

    hm = make_human_model_with(stats, config)

    # Call the protected method
    hm._update_stats()

    assert stats.instance_cost == 1.5
    assert stats.api_calls == 1


def test_update_stats_raises_instance_cost_limit():
    # Set up so that after adding cost_per_call we exceed per_instance_cost_limit,
    # but total_cost_limit is higher so the InstanceCostLimitExceededError is the one raised first.
    stats = SimpleNamespace(instance_cost=4.0, api_calls=2)
    config = SimpleNamespace(cost_per_call=2.5, per_instance_cost_limit=6.0, total_cost_limit=100.0)

    hm = make_human_model_with(stats, config)

    with pytest.raises(InstanceCostLimitExceededError) as excinfo:
        hm._update_stats()

    # The stats should have been updated before the exception is raised
    assert stats.instance_cost == 6.5  # 4.0 + 2.5
    assert stats.api_calls == 3

    expected_msg = f"Instance cost limit exceeded: {stats.instance_cost} > {config.per_instance_cost_limit}"
    assert expected_msg in str(excinfo.value)


def test_update_stats_raises_total_cost_limit_only():
    # Arrange so that after adding cost_per_call the instance_cost is > total_cost_limit
    # but still <= per_instance_cost_limit, so the TotalCostLimitExceededError is raised.
    stats = SimpleNamespace(instance_cost=8.0, api_calls=5)
    config = SimpleNamespace(cost_per_call=3.0, per_instance_cost_limit=20.0, total_cost_limit=10.0)

    hm = make_human_model_with(stats, config)

    with pytest.raises(TotalCostLimitExceededError) as excinfo:
        hm._update_stats()

    # Stats should be updated before the exception
    assert stats.instance_cost == 11.0  # 8.0 + 3.0
    assert stats.api_calls == 6

    expected_msg = f"Total cost limit exceeded: {stats.instance_cost} > {config.total_cost_limit}"
    assert expected_msg in str(excinfo.value)
