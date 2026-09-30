import pytest
from types import SimpleNamespace

from sweagent.agent.reviewer import ScoreRetryLoop


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg: str) -> None:
        # deterministic side-effect: record messages for assertions
        self.messages.append(msg)


def _make_loop(*, reviews=None, n_attempts=0, n_accepted=0, instance_cost=0.0, cost_limit=0.0,
               max_attempts=0, max_accepts=0, min_budget_for_new_attempt=0.0):
    """
    Create a plain object (SimpleNamespace) with the attributes that ScoreRetryLoop.retry
    expects. We avoid creating a ScoreRetryLoop instance to sidestep class-level
    property descriptors (which prevented attribute assignment).
    """
    fake = SimpleNamespace()
    fake._reviews = reviews if reviews is not None else []
    # Use plain attributes on this fake object; ScoreRetryLoop.retry will be called
    # as an unbound function with this object as self, so no class properties apply.
    fake._n_attempts = n_attempts
    fake._n_accepted = n_accepted
    fake._total_stats = SimpleNamespace(instance_cost=instance_cost)
    fake._config = SimpleNamespace(
        cost_limit=cost_limit,
        max_attempts=max_attempts,
        max_accepts=max_accepts,
        min_budget_for_new_attempt=min_budget_for_new_attempt,
    )
    fake.logger = DummyLogger()
    return fake


def test_cost_limit_exceeded_round_019():
    # Setup: total cost exceeds a positive cost limit -> should exit with False
    reviews = [SimpleNamespace(accept=0.5), SimpleNamespace(accept=0.9)]
    loop = _make_loop(reviews=reviews, n_attempts=3, n_accepted=1,
                      instance_cost=150.0, cost_limit=100.0,
                      max_attempts=10, max_accepts=10, min_budget_for_new_attempt=0.0)

    # Call the unbound function with our fake object to avoid class property conflicts
    result = ScoreRetryLoop.retry(loop)

    assert result is False
    # Log must contain the stat_str and the 'exceeds cost limit' reason
    assert loop.logger.messages, "Expected logger.info to be called"
    last = loop.logger.messages[-1]
    # stat_str is built from n_attempts, max_score and n_accepted
    assert "n_samples=3" in last
    assert "max_score=0.9" in last
    assert "n_accepted=1" in last
    assert "exceeds cost limit" in last


def test_max_attempts_reached_round_019():
    # Setup: cost limit not exceeded, but n_attempts >= max_attempts -> exit False
    reviews = [SimpleNamespace(accept=-0.1)]
    loop = _make_loop(reviews=reviews, n_attempts=5, n_accepted=0,
                      instance_cost=0.0, cost_limit=1000.0,
                      max_attempts=5, max_accepts=10, min_budget_for_new_attempt=0.0)

    result = ScoreRetryLoop.retry(loop)

    assert result is False
    assert loop.logger.messages, "Expected logger.info to be called"
    last = loop.logger.messages[-1]
    assert "n_samples=5" in last
    assert "max_score=-0.1" in last
    assert "max_attempts=5" in last


def test_max_accepts_reached_round_019():
    # Setup: earlier exits disabled, but n_accepted >= max_accepts -> exit False
    reviews = [SimpleNamespace(accept=1.0), SimpleNamespace(accept=0.2)]
    loop = _make_loop(reviews=reviews, n_attempts=1, n_accepted=2,
                      instance_cost=0.0, cost_limit=1000.0,
                      max_attempts=10, max_accepts=2, min_budget_for_new_attempt=0.0)

    result = ScoreRetryLoop.retry(loop)

    assert result is False
    assert loop.logger.messages, "Expected logger.info to be called"
    last = loop.logger.messages[-1]
    assert "n_samples=1" in last
    assert "max_score=1.0" in last
    assert "max_accepts=2" in last


def test_not_enough_budget_for_new_attempt_round_019():
    # Setup: none of the earlier exit conditions apply, but remaining budget < min_budget_for_new_attempt
    reviews = [SimpleNamespace(accept=0.0)]
    loop = _make_loop(reviews=reviews, n_attempts=0, n_accepted=0,
                      instance_cost=90.0, cost_limit=100.0,
                      max_attempts=10, max_accepts=10, min_budget_for_new_attempt=20.0)

    # remaining_budget = 10 < 20 so it should exit
    result = ScoreRetryLoop.retry(loop)

    assert result is False
    assert loop.logger.messages, "Expected logger.info to be called"
    last = loop.logger.messages[-1]
    assert "Not enough budget left for a new attempt" in last
    assert "n_samples=0" in last
    assert "max_score=0.0" in last


def test_all_conditions_pass_round_019():
    # Setup: no exit conditions should trigger -> retry returns True
    # Use a non-empty reviews list to ensure max_score is computed (not default)
    reviews = [SimpleNamespace(accept=2.5), SimpleNamespace(accept=1.0)]
    loop = _make_loop(reviews=reviews, n_attempts=0, n_accepted=0,
                      instance_cost=0.0, cost_limit=0.0,
                      max_attempts=0, max_accepts=0, min_budget_for_new_attempt=0.0)

    result = ScoreRetryLoop.retry(loop)

    assert result is True
    # No exit log should have been emitted
    assert loop.logger.messages == []
