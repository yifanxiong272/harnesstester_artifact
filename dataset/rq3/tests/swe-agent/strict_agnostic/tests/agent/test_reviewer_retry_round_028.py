import types
from types import SimpleNamespace

from sweagent.agent import reviewer as reviewer_mod


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg):
        # deterministic capture of messages for assertions
        self.messages.append(str(msg))


def _call_retry_with(fake_self):
    # Call the unbound retry function with our fake "self" object
    return reviewer_mod.ChooserRetryLoop.retry(fake_self)


def test_cost_limit_exceeded_round_028():
    """When total instance cost exceeds cost_limit (>0), retry() returns False and logs reason."""
    fake = SimpleNamespace()
    fake._n_attempts = 3
    fake._total_stats = SimpleNamespace(instance_cost=250.0)
    # cost_limit > 0 and instance_cost > cost_limit triggers first branch
    fake._config = SimpleNamespace(cost_limit=200.0, max_attempts=0, min_budget_for_new_attempt=0)
    fake.logger = DummyLogger()

    result = _call_retry_with(fake)

    assert result is False
    # Ensure a useful, specific message was logged
    assert any("exceeds cost limit" in m or "exceeds cost" in m for m in fake.logger.messages), (
        f"Expected cost-exceeded message in logs, got: {fake.logger.messages}"
    )


def test_max_attempts_reached_round_028():
    """When n_attempts >= max_attempts > 0, retry() returns False and logs max_attempts reached."""
    fake = SimpleNamespace()
    # Put instance cost below limit so first branch is not triggered
    fake._total_stats = SimpleNamespace(instance_cost=10.0)
    fake._config = SimpleNamespace(cost_limit=100.0, max_attempts=2, min_budget_for_new_attempt=0)
    # set n_attempts equal to max_attempts to trigger branch
    fake._n_attempts = 2
    fake.logger = DummyLogger()

    result = _call_retry_with(fake)

    assert result is False
    assert any("max_attempts" in m or "max_attempts=" in m for m in fake.logger.messages), (
        f"Expected max_attempts message in logs, got: {fake.logger.messages}"
    )


def test_not_enough_budget_round_028():
    """When remaining budget < min_budget_for_new_attempt (>0), retry() returns False and logs not enough budget."""
    fake = SimpleNamespace()
    fake._total_stats = SimpleNamespace(instance_cost=120.0)
    # remaining_budget = 150 - 120 = 30 < min_budget_for_new_attempt (50)
    fake._config = SimpleNamespace(cost_limit=150.0, max_attempts=0, min_budget_for_new_attempt=50.0)
    fake._n_attempts = 1
    fake.logger = DummyLogger()

    result = _call_retry_with(fake)

    assert result is False
    assert any("Not enough budget" in m or "Not enough" in m for m in fake.logger.messages), (
        f"Expected not-enough-budget message in logs, got: {fake.logger.messages}"
    )


def test_retry_allowed_round_028():
    """When none of the exit conditions apply, retry() returns True."""
    fake = SimpleNamespace()
    fake._total_stats = SimpleNamespace(instance_cost=10.0)
    # Set cost_limit and max_attempts such that none of the >0 chained checks trigger
    fake._config = SimpleNamespace(cost_limit=1000.0, max_attempts=0, min_budget_for_new_attempt=0)
    fake._n_attempts = 0
    fake.logger = DummyLogger()

    result = _call_retry_with(fake)

    assert result is True
    # No messages should have been logged for early exit
    assert fake.logger.messages == [], f"Expected no exit messages, got: {fake.logger.messages}"
