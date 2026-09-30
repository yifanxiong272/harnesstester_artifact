import pytest
from types import SimpleNamespace

from sweagent.agent.models import HumanModel
from sweagent.exceptions import (
    InstanceCostLimitExceededError,
    TotalCostLimitExceededError,
)


def _make_human_model(stats=None, config=None):
    """Construct a HumanModel instance without running __init__.

    We use object.__new__ to avoid side effects from the real initializer
    and then attach plain SimpleNamespace objects for stats and config.
    """
    hm = object.__new__(HumanModel)
    hm.stats = stats or SimpleNamespace(instance_cost=0.0, api_calls=0)
    hm.config = config or SimpleNamespace(
        cost_per_call=1.0, per_instance_cost_limit=1e9, total_cost_limit=1e12
    )
    return hm


def test_update_stats_increments_without_breach_round_046():
    # Arrange: set generous limits so no exception should be raised
    stats = SimpleNamespace(instance_cost=0.0, api_calls=0)
    config = SimpleNamespace(cost_per_call=2.5, per_instance_cost_limit=100.0, total_cost_limit=1000.0)
    hm = _make_human_model(stats=stats, config=config)

    # Act
    hm._update_stats()

    # Assert: stats were updated deterministically
    assert hm.stats.instance_cost == 2.5
    assert hm.stats.api_calls == 1


def test_update_stats_raises_instance_limit_round_046():
    # Arrange: after adding cost_per_call we exceed per-instance limit
    stats = SimpleNamespace(instance_cost=9.0, api_calls=0)
    # cost_per_call 2.0 -> new instance_cost 11.0 which is > per_instance_cost_limit 10.0
    config = SimpleNamespace(cost_per_call=2.0, per_instance_cost_limit=10.0, total_cost_limit=100.0)
    hm = _make_human_model(stats=stats, config=config)

    # Act / Assert: InstanceCostLimitExceededError is raised and stats were incremented before raising
    with pytest.raises(InstanceCostLimitExceededError) as excinfo:
        hm._update_stats()

    # The method increments instance_cost and api_calls before checking limits
    assert hm.stats.instance_cost == 11.0
    assert hm.stats.api_calls == 1

    # The exception message should include the numeric values used
    msg = str(excinfo.value)
    assert "Instance cost limit exceeded" in msg
    assert "11.0" in msg and "10.0" in msg


def test_update_stats_raises_total_limit_only_round_046():
    # Arrange: per-instance limit is high, total limit is low -> triggers total-limit branch
    stats = SimpleNamespace(instance_cost=9.0, api_calls=0)
    # cost_per_call 2.0 -> new instance_cost 11.0 which is <= per_instance_cost_limit 100.0
    # but > total_cost_limit 10.0
    config = SimpleNamespace(cost_per_call=2.0, per_instance_cost_limit=100.0, total_cost_limit=10.0)
    hm = _make_human_model(stats=stats, config=config)

    # Act / Assert: TotalCostLimitExceededError is raised and stats were incremented before raising
    with pytest.raises(TotalCostLimitExceededError) as excinfo:
        hm._update_stats()

    assert hm.stats.instance_cost == 11.0
    assert hm.stats.api_calls == 1

    msg = str(excinfo.value)
    assert "Total cost limit exceeded" in msg
    assert "11.0" in msg and "10.0" in msg
