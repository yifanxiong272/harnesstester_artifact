# file: sweagent/agent/models.py:604-642
# asked: {"lines": [628, 629, 630, 633, 634, 636, 637, 640, 641, 642], "branches": [[627, 628], [632, 633], [639, 640]]}
# gained: {"lines": [628, 629, 630, 633, 634, 636, 637, 640, 641, 642], "branches": [[627, 628], [632, 633], [639, 640]]}

import threading
import types
import pytest

from types import SimpleNamespace

from sweagent.agent import models as models_module
from sweagent.agent.models import LiteLLMModel, InstanceStats, GLOBAL_STATS
from sweagent.exceptions import (
    InstanceCallLimitExceededError,
    InstanceCostLimitExceededError,
    TotalCostLimitExceededError,
)


class DummyLogger:
    def __init__(self):
        self.debug_msgs = []
        self.warn_msgs = []

    def debug(self, msg):
        self.debug_msgs.append(msg)

    def warning(self, msg):
        self.warn_msgs.append(msg)


def make_instance_with_config(config_kwargs: dict, stats: InstanceStats | None = None):
    # Create LiteLLMModel instance without running __init__
    inst = LiteLLMModel.__new__(LiteLLMModel)
    # Provide a simple config object with required attributes
    inst.config = SimpleNamespace(**config_kwargs)
    # Provide InstanceStats
    inst.stats = stats if stats is not None else InstanceStats()
    inst.logger = DummyLogger()
    return inst


def reset_global_total():
    # Ensure GLOBAL_STATS.total_cost reset to 0
    GLOBAL_STATS.total_cost = 0.0


def test_total_cost_limit_exceeded_resets_and_updates_stats():
    reset_global_total()
    try:
        inst = make_instance_with_config(
            {"total_cost_limit": 0.5, "per_instance_cost_limit": 0.0, "per_instance_call_limit": 0}
        )

        # Preconditions
        assert GLOBAL_STATS.total_cost == 0.0
        assert inst.stats.instance_cost == 0.0
        assert inst.stats.tokens_sent == 0
        assert inst.stats.tokens_received == 0
        assert inst.stats.api_calls == 0

        with pytest.raises(TotalCostLimitExceededError) as exc:
            inst._update_stats(input_tokens=3, output_tokens=5, cost=1.0)

        # Exception message check
        assert "Total cost limit exceeded" in str(exc.value)

        # GLOBAL_STATS should have been incremented before the exception
        assert GLOBAL_STATS.total_cost == pytest.approx(1.0)

        # Instance stats should have been updated before the exception
        assert inst.stats.instance_cost == pytest.approx(1.0)
        assert inst.stats.tokens_sent == 3
        assert inst.stats.tokens_received == 5
        assert inst.stats.api_calls == 1

        # Logger should have recorded a warning about total cost
        assert any("exceeds limit" in m for m in inst.logger.warn_msgs)
    finally:
        reset_global_total()


def test_instance_cost_limit_exceeded_updates_stats_and_raises():
    reset_global_total()
    try:
        inst = make_instance_with_config(
            {"total_cost_limit": 0.0, "per_instance_cost_limit": 0.5, "per_instance_call_limit": 0}
        )
        # Ensure starting instance cost zero
        assert inst.stats.instance_cost == 0.0

        with pytest.raises(InstanceCostLimitExceededError) as exc:
            inst._update_stats(input_tokens=2, output_tokens=2, cost=1.0)

        assert "Instance cost limit exceeded" in str(exc.value)

        # GLOBAL_STATS should have been incremented
        assert GLOBAL_STATS.total_cost == pytest.approx(1.0)

        # Instance stats should reflect the added cost and tokens
        assert inst.stats.instance_cost == pytest.approx(1.0)
        assert inst.stats.tokens_sent == 2
        assert inst.stats.tokens_received == 2
        assert inst.stats.api_calls == 1

        # Logger should have a warning mentioning instance cost exceed
        assert any("exceeds limit" in m for m in inst.logger.warn_msgs)
    finally:
        reset_global_total()


def test_instance_call_limit_exceeded_after_increment():
    reset_global_total()
    try:
        # Start with api_calls = 1 so that after increment it becomes 2 and triggers per_instance_call_limit=1
        starting_stats = InstanceStats(instance_cost=0.0, tokens_sent=0, tokens_received=0, api_calls=1)
        inst = make_instance_with_config(
            {"total_cost_limit": 0.0, "per_instance_cost_limit": 0.0, "per_instance_call_limit": 1},
            stats=starting_stats,
        )

        with pytest.raises(InstanceCallLimitExceededError) as exc:
            inst._update_stats(input_tokens=0, output_tokens=0, cost=0.0)

        assert "Per instance call limit exceeded" in str(exc.value)

        # api_calls should have been incremented before the exception
        assert inst.stats.api_calls == 2

        # cost was 0.0, GLOBAL_STATS should remain unchanged (but was modified by method: adding 0.0)
        assert GLOBAL_STATS.total_cost == pytest.approx(0.0)

        # Ensure warning was logged about API calls limit
        assert any("API calls" in m or "exceeds limit" in m for m in inst.logger.warn_msgs)
    finally:
        reset_global_total()
