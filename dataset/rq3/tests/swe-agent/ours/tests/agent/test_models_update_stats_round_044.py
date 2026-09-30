import types
import pytest

from sweagent.agent import models
from sweagent.exceptions import (
    InstanceCostLimitExceededError,
    TotalCostLimitExceededError,
)

# Tests for HumanModel._update_stats behavior around cost limits.

def test_update_stats_no_limit_round_044():
    """When costs are below both per-instance and total limits, stats update without exception."""
    fake_stats = types.SimpleNamespace(instance_cost=0.0, api_calls=0)
    fake_config = types.SimpleNamespace(cost_per_call=1.0, per_instance_cost_limit=100.0, total_cost_limit=1000.0)
    fake_self = types.SimpleNamespace(stats=fake_stats, config=fake_config)

    # Call the unbound method with our fake self
    models.HumanModel._update_stats(fake_self)

    assert fake_stats.instance_cost == 1.0
    assert fake_stats.api_calls == 1


def test_update_stats_instance_limit_exceeded_round_044():
    """If instance_cost exceeds per_instance_cost_limit after increment, InstanceCostLimitExceededError is raised and stats were updated."""
    # Start with some instance cost; choose cost_per_call so the increment pushes over per-instance limit
    fake_stats = types.SimpleNamespace(instance_cost=10.0, api_calls=5)
    fake_config = types.SimpleNamespace(cost_per_call=100.0, per_instance_cost_limit=50.0, total_cost_limit=1000.0)
    fake_self = types.SimpleNamespace(stats=fake_stats, config=fake_config)

    with pytest.raises(InstanceCostLimitExceededError) as excinfo:
        models.HumanModel._update_stats(fake_self)

    # After the method attempted the update, instance_cost and api_calls should have been incremented
    assert fake_stats.instance_cost == 110.0
    assert fake_stats.api_calls == 6

    # The exception message should contain the numeric values from the config and stats
    msg = str(excinfo.value)
    assert "Instance cost limit exceeded" in msg
    assert "110.0" in msg
    assert "50.0" in msg


def test_update_stats_total_limit_exceeded_round_044():
    """If instance_cost exceeds total_cost_limit but not per_instance_cost_limit, TotalCostLimitExceededError is raised and stats were updated."""
    # Set per-instance limit high so it's not triggered, but total limit low so increment triggers it
    fake_stats = types.SimpleNamespace(instance_cost=30.0, api_calls=2)
    fake_config = types.SimpleNamespace(cost_per_call=40.0, per_instance_cost_limit=1000.0, total_cost_limit=50.0)
    fake_self = types.SimpleNamespace(stats=fake_stats, config=fake_config)

    with pytest.raises(TotalCostLimitExceededError) as excinfo:
        models.HumanModel._update_stats(fake_self)

    # Ensure the stats were updated before the total-limit check raised
    assert fake_stats.instance_cost == 70.0
    assert fake_stats.api_calls == 3

    msg = str(excinfo.value)
    assert "Total cost limit exceeded" in msg
    assert "70.0" in msg
    assert "50.0" in msg
