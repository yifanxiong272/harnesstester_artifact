# file: sweagent/agent/reviewer.py:524-546
# asked: {"lines": [525, 526, 527, 528, 529, 531, 533, 534, 535, 537, 538, 539, 540, 541, 543, 544, 546], "branches": [[526, 527], [526, 533], [533, 534], [533, 537], [538, 539], [538, 546]]}
# gained: {"lines": [525, 526, 527, 528, 529, 531, 533, 534, 535, 537, 538, 539, 540, 541, 543, 544, 546], "branches": [[526, 527], [526, 533], [533, 534], [533, 537], [538, 539], [538, 546]]}

import pytest
from types import SimpleNamespace

from sweagent.agent.reviewer import ChooserRetryLoop


class DummyLogger:
    def __init__(self):
        self.infos = []

    def info(self, msg):
        self.infos.append(msg)


def make_instance(monkeypatch, total_cost: int, n_attempts: int, *, cost_limit=100, max_attempts=10, min_budget_for_new_attempt=0):
    """
    Create a ChooserRetryLoop instance without calling __init__, and monkeypatch the
    _total_stats and _n_attempts properties on the class to return the provided values.
    Returns (instance, dummy_logger). The monkeypatch fixture will restore patched attributes.
    """
    # Prepare stats and attempts values
    stats = SimpleNamespace(instance_cost=total_cost)

    # Patch the properties on the class so they return our test values
    monkeypatch.setattr(
        ChooserRetryLoop,
        "_total_stats",
        property(lambda self, stats=stats: stats),
        raising=True,
    )
    monkeypatch.setattr(
        ChooserRetryLoop,
        "_n_attempts",
        property(lambda self, val=n_attempts: val),
        raising=True,
    )

    # Create bare instance (bypass __init__) and attach a config and dummy logger
    inst = object.__new__(ChooserRetryLoop)
    inst._config = SimpleNamespace(
        cost_limit=cost_limit,
        max_attempts=max_attempts,
        min_budget_for_new_attempt=min_budget_for_new_attempt,
        chooser=None,
    )
    dummy_logger = DummyLogger()
    inst.logger = dummy_logger
    return inst, dummy_logger


def test_retry_exits_when_total_cost_exceeds_cost_limit(monkeypatch):
    # total cost greater than cost_limit (>0) should cause retry() to return False
    inst, logger = make_instance(
        monkeypatch,
        total_cost=150,
        n_attempts=3,
        cost_limit=100,  # cost_limit > 0 and less than total_cost
        max_attempts=10,
        min_budget_for_new_attempt=0,
    )

    result = inst.retry()
    assert result is False
    # Expect logger was called and message mentions cost and stat_str with n_samples=3
    assert any("exceeds cost limit" in m for m in logger.infos), logger.infos
    assert any("n_samples=3" in m for m in logger.infos), logger.infos


def test_retry_exits_when_max_attempts_reached(monkeypatch):
    # n_attempts >= max_attempts (>0) should cause retry() to return False
    inst, logger = make_instance(
        monkeypatch,
        total_cost=10,
        n_attempts=2,
        cost_limit=100,
        max_attempts=2,  # equal -> should exit
        min_budget_for_new_attempt=0,
    )

    result = inst.retry()
    assert result is False
    assert any("max_attempts=2 reached" in m for m in logger.infos), logger.infos
    assert any("n_samples=2" in m for m in logger.infos), logger.infos


def test_retry_exits_when_not_enough_min_budget_for_new_attempt(monkeypatch):
    # remaining_budget < min_budget_for_new_attempt and min_budget_for_new_attempt > 0 -> False
    inst, logger = make_instance(
        monkeypatch,
        total_cost=80,
        n_attempts=1,
        cost_limit=100,  # remaining_budget = 20
        max_attempts=10,
        min_budget_for_new_attempt=50,  # requires 50, only 20 remaining
    )

    result = inst.retry()
    assert result is False
    # Message should mention "Not enough budget left" and include remaining and required numbers
    assert any("Not enough budget left" in m for m in logger.infos), logger.infos
    assert any("n_samples=1" in m for m in logger.infos), logger.infos
    # Check that remaining_budget and required value show up in the message
    assert any("20 remaining" in m and "50 required" in m for m in logger.infos), logger.infos


def test_retry_allows_new_attempt_when_conditions_pass(monkeypatch):
    # All conditions satisfied -> retry() should return True
    inst, logger = make_instance(
        monkeypatch,
        total_cost=10,
        n_attempts=1,
        cost_limit=100,
        max_attempts=10,
        min_budget_for_new_attempt=5,  # remaining_budget = 90 >= 5
    )

    result = inst.retry()
    assert result is True
    # No info messages should indicate exits for the above conditions
    assert all("Exiting retry loop" not in m for m in logger.infos), logger.infos
