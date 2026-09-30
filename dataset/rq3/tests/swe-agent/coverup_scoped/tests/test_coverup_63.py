# file: sweagent/agent/agents.py:246-249
# asked: {"lines": [248, 249], "branches": []}
# gained: {"lines": [248, 249], "branches": []}

import pytest
from types import SimpleNamespace

from sweagent.agent.agents import RetryAgent
from sweagent.agent.models import InstanceStats


def test_total_instance_stats_assert_raised():
    # Create an instance without running __init__
    ra = object.__new__(RetryAgent)
    # Explicitly set _rloop to None to trigger the assertion in the property
    ra._rloop = None
    ra._total_instance_attempt_stats = InstanceStats()
    with pytest.raises(AssertionError):
        _ = ra._total_instance_stats


def test_total_instance_stats_returns_sum():
    # Create an instance without running __init__
    ra = object.__new__(RetryAgent)
    # Set attempt stats
    ra._total_instance_attempt_stats = InstanceStats(
        instance_cost=1.5, tokens_sent=10, tokens_received=2, api_calls=1
    )
    # Set rloop with review_model_stats
    ra._rloop = SimpleNamespace(
        review_model_stats=InstanceStats(
            instance_cost=2.25, tokens_sent=5, tokens_received=3, api_calls=2
        )
    )

    result = ra._total_instance_stats

    assert isinstance(result, InstanceStats)
    assert result.instance_cost == pytest.approx(1.5 + 2.25)
    assert result.tokens_sent == 10 + 5
    assert result.tokens_received == 2 + 3
    assert result.api_calls == 1 + 2
