import types
import pytest
from types import SimpleNamespace

import sweagent.agent.models as models
from sweagent.exceptions import (
    TotalCostLimitExceededError,
    InstanceCostLimitExceededError,
    InstanceCallLimitExceededError,
)


class DummyStats:
    def __init__(self, instance_cost=0.0, tokens_sent=0, tokens_received=0, api_calls=0):
        self.instance_cost = instance_cost
        self.tokens_sent = tokens_sent
        self.tokens_received = tokens_received
        self.api_calls = api_calls


class DummyConfig:
    def __init__(self, total_cost_limit=0.0, per_instance_cost_limit=0.0, per_instance_call_limit=0):
        self.total_cost_limit = total_cost_limit
        self.per_instance_cost_limit = per_instance_cost_limit
        self.per_instance_call_limit = per_instance_call_limit


class CaptureLogger:
    def __init__(self):
        self.debug_messages = []
        self.warning_messages = []

    def debug(self, msg):
        # keep exactly what the target code would pass: strings
        self.debug_messages.append(str(msg))

    def warning(self, msg):
        self.warning_messages.append(str(msg))


class DummyGlobal:
    def __init__(self, total_cost=0.0):
        self.total_cost = total_cost


class DummyLock:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False


def _bound_update(self, input_tokens, output_tokens, cost):
    # helper: call the unbound function on a fabricated self
    # access the original function object from the class and call with the fake self
    func = models.LiteLLMModel._update_stats
    return func(self, input_tokens=input_tokens, output_tokens=output_tokens, cost=cost)


def test_update_stats_normal_round_045(monkeypatch):
    """Verify stats and logs update when limits are not exceeded."""
    # Arrange: deterministic globals
    monkeypatch.setattr(models, "GLOBAL_STATS", DummyGlobal(total_cost=0.0), raising=False)
    monkeypatch.setattr(models, "GLOBAL_STATS_LOCK", DummyLock(), raising=False)

    stats = DummyStats(instance_cost=0.0, tokens_sent=0, tokens_received=0, api_calls=0)
    config = DummyConfig(total_cost_limit=0.0, per_instance_cost_limit=0.0, per_instance_call_limit=0)
    logger = CaptureLogger()

    fake_self = SimpleNamespace(stats=stats, config=config, logger=logger)

    # Act
    _bound_update(fake_self, input_tokens=10, output_tokens=5, cost=0.5)

    # Assert: numeric updates
    assert models.GLOBAL_STATS.total_cost == pytest.approx(0.5)
    assert fake_self.stats.instance_cost == pytest.approx(0.5)
    assert fake_self.stats.tokens_sent == 10
    assert fake_self.stats.tokens_received == 5
    assert fake_self.stats.api_calls == 1

    # Assert: logger.debug called at least twice and contains token/cost info
    assert len(logger.debug_messages) >= 2
    combined = " ".join(logger.debug_messages)
    assert "input_tokens=10" in combined
    assert "output_tokens=5" in combined
    assert "instance_cost=0.50" in combined


def test_update_stats_raises_total_cost_limit_round_045(monkeypatch):
    """When GLOBAL_STATS.total_cost after update exceeds config.total_cost_limit, TotalCostLimitExceededError is raised and warning logged."""
    # Arrange: set GLOBAL_STATS such that after adding cost it will exceed limit
    monkeypatch.setattr(models, "GLOBAL_STATS", DummyGlobal(total_cost=4.5), raising=False)
    monkeypatch.setattr(models, "GLOBAL_STATS_LOCK", DummyLock(), raising=False)

    stats = DummyStats(instance_cost=0.0, tokens_sent=0, tokens_received=0, api_calls=0)
    # set a positive total_cost_limit to trigger the first branch
    config = DummyConfig(total_cost_limit=5.0, per_instance_cost_limit=0.0, per_instance_call_limit=0)
    logger = CaptureLogger()

    fake_self = SimpleNamespace(stats=stats, config=config, logger=logger)

    # Act & Assert
    with pytest.raises(TotalCostLimitExceededError) as excinfo:
        _bound_update(fake_self, input_tokens=1, output_tokens=1, cost=1.0)

    # Check that the warning was emitted with formatted amounts (two decimals)
    assert any("exceeds limit" in msg for msg in logger.warning_messages)
    # ensure the message contains formatted total cost and limit to two decimals
    assert any("5.50" in msg or "5.5" in msg for msg in logger.warning_messages)
    assert str(excinfo.value) == "Total cost limit exceeded"


def test_update_stats_raises_instance_cost_limit_round_045(monkeypatch):
    """When per-instance cost after update exceeds per_instance_cost_limit, InstanceCostLimitExceededError is raised and warning logged."""
    # Arrange: ensure global total limit won't trigger
    monkeypatch.setattr(models, "GLOBAL_STATS", DummyGlobal(total_cost=0.0), raising=False)
    monkeypatch.setattr(models, "GLOBAL_STATS_LOCK", DummyLock(), raising=False)

    # instance already has some cost; after adding cost it will exceed the per-instance limit
    stats = DummyStats(instance_cost=1.5, tokens_sent=0, tokens_received=0, api_calls=0)
    config = DummyConfig(total_cost_limit=0.0, per_instance_cost_limit=2.0, per_instance_call_limit=0)
    logger = CaptureLogger()

    fake_self = SimpleNamespace(stats=stats, config=config, logger=logger)

    with pytest.raises(InstanceCostLimitExceededError) as excinfo:
        _bound_update(fake_self, input_tokens=0, output_tokens=0, cost=1.0)

    assert any("exceeds limit" in msg for msg in logger.warning_messages)
    assert str(excinfo.value) == "Instance cost limit exceeded"


def test_update_stats_raises_call_limit_round_045(monkeypatch):
    """When per-instance API calls after increment exceed per_instance_call_limit, InstanceCallLimitExceededError is raised and warning logged."""
    # Arrange: ensure cost-based limits are non-positive so they don't trigger earlier
    monkeypatch.setattr(models, "GLOBAL_STATS", DummyGlobal(total_cost=0.0), raising=False)
    monkeypatch.setattr(models, "GLOBAL_STATS_LOCK", DummyLock(), raising=False)

    # start with api_calls = 1; the method increments it to 2 before the check
    stats = DummyStats(instance_cost=0.0, tokens_sent=0, tokens_received=0, api_calls=1)
    # set call limit to 1 so that after the increment it will be exceeded
    config = DummyConfig(total_cost_limit=0.0, per_instance_cost_limit=0.0, per_instance_call_limit=1)
    logger = CaptureLogger()

    fake_self = SimpleNamespace(stats=stats, config=config, logger=logger)

    with pytest.raises(InstanceCallLimitExceededError) as excinfo:
        _bound_update(fake_self, input_tokens=0, output_tokens=0, cost=0.0)

    # warning message should mention the new api_calls value (2) and the limit (1)
    assert any("API calls" in msg and "exceeds limit" in msg for msg in logger.warning_messages)
    assert any("2" in msg and "1" in msg for msg in logger.warning_messages)
    assert str(excinfo.value) == "Per instance call limit exceeded"
