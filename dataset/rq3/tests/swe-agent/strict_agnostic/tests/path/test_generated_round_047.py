import pytest
from types import SimpleNamespace
from sweagent.agent import models
from sweagent.exceptions import (
    TotalCostLimitExceededError,
    InstanceCostLimitExceededError,
    InstanceCallLimitExceededError,
)


def _make_dummy():
    """Create a simple dummy 'self' object compatible with
    LiteLLMModel._update_stats. Returns (self, logger, stats, config).
    """
    stats = SimpleNamespace(instance_cost=0.0, tokens_sent=0, tokens_received=0, api_calls=0)
    config = SimpleNamespace(total_cost_limit=0.0, per_instance_cost_limit=0.0, per_instance_call_limit=0)

    class DummyLogger:
        def __init__(self):
            self.debug_msgs = []
            self.warn_msgs = []

        def debug(self, msg):
            # preserve messages for assertions
            self.debug_msgs.append(str(msg))

        def warning(self, msg):
            self.warn_msgs.append(str(msg))

    logger = DummyLogger()
    self = SimpleNamespace(stats=stats, config=config, logger=logger)
    return self, logger, stats, config


def test_total_cost_limit_exceeded_round_047():
    """Trigger the total-cost-limit branch (lines ~627-630).

    - Ensure GLOBAL_STATS.total_cost increases by the cost.
    - Assert TotalCostLimitExceededError is raised.
    - Assert a warning containing 'exceeds limit' was emitted.
    """
    obj, logger, stats, config = _make_dummy()

    # Start from a known global state
    models.GLOBAL_STATS.total_cost = 0.0

    # Set limits so that after adding cost the global limit is exceeded
    config.total_cost_limit = 1.0
    config.per_instance_cost_limit = 0.0
    config.per_instance_call_limit = 0

    # Call should raise TotalCostLimitExceededError after incrementing global total
    with pytest.raises(TotalCostLimitExceededError) as excinfo:
        models.LiteLLMModel._update_stats(obj, input_tokens=10, output_tokens=5, cost=2.0)

    # Confirm exception text
    assert "Total cost limit exceeded" in str(excinfo.value)

    # Logger should have received a warning about the cost exceeding the limit
    assert any("exceeds limit" in m for m in logger.warn_msgs), "expected a warning mentioning 'exceeds limit'"

    # Global total cost should have been updated (2.0 was added)
    assert models.GLOBAL_STATS.total_cost == pytest.approx(2.0)


def test_instance_cost_limit_exceeded_round_047():
    """Trigger the per-instance-cost-limit branch (lines ~632-637).

    - Ensure instance cost is updated.
    - Assert InstanceCostLimitExceededError is raised when instance cost exceeds the per-instance limit.
    - Assert a warning containing 'exceeds limit' was emitted and instance_cost updated.
    """
    obj, logger, stats, config = _make_dummy()

    # Reset global state so total_cost check does not interfere
    models.GLOBAL_STATS.total_cost = 0.0

    config.total_cost_limit = 0.0
    config.per_instance_cost_limit = 1.0
    config.per_instance_call_limit = 0

    stats.instance_cost = 0.0

    # cost > per_instance_cost_limit -> should raise InstanceCostLimitExceededError
    with pytest.raises(InstanceCostLimitExceededError):
        models.LiteLLMModel._update_stats(obj, input_tokens=0, output_tokens=0, cost=2.5)

    # Instance cost should have been increased by the cost
    assert stats.instance_cost == pytest.approx(2.5)

    # A warning about instance cost exceeding the per-instance limit should have been emitted
    assert any("exceeds limit" in m for m in logger.warn_msgs), "expected a warning about instance cost exceeding the limit"


def test_instance_call_limit_exceeded_round_047():
    """Trigger the per-instance-call-limit branch (lines ~639-642).

    - Set api_calls such that the increment in _update_stats pushes it above the per-instance-call-limit.
    - Assert InstanceCallLimitExceededError is raised and a warning mentioning API calls was emitted.
    """
    obj, logger, stats, config = _make_dummy()

    models.GLOBAL_STATS.total_cost = 0.0

    config.total_cost_limit = 0.0
    config.per_instance_cost_limit = 0.0

    # Set per-instance-call-limit to 1, and current api_calls to 1 so that after +1 it becomes 2 > 1
    config.per_instance_call_limit = 1
    stats.api_calls = 1

    with pytest.raises(InstanceCallLimitExceededError):
        models.LiteLLMModel._update_stats(obj, input_tokens=0, output_tokens=0, cost=0.0)

    # api_calls should have been incremented
    assert stats.api_calls == 2

    # And a warning about API calls exceeding the limit should have been emitted
    assert any("API calls" in m for m in logger.warn_msgs), "expected a warning mentioning API calls"
