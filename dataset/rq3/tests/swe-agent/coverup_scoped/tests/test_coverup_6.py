# file: sweagent/agent/reviewer.py:617-645
# asked: {"lines": [618, 619, 621, 622, 623, 624, 626, 628, 629, 630, 632, 633, 634, 636, 637, 638, 639, 640, 642, 643, 645], "branches": [[621, 622], [621, 628], [628, 629], [628, 632], [632, 633], [632, 636], [637, 638], [637, 645]]}
# gained: {"lines": [618, 619, 621, 622, 623, 624, 626, 628, 629, 630, 632, 633, 634, 636, 637, 638, 639, 640, 642, 643, 645], "branches": [[621, 622], [621, 628], [628, 629], [628, 632], [632, 633], [632, 636], [637, 638], [637, 645]]}

import types
from types import SimpleNamespace
import pytest

from sweagent.agent.reviewer import ScoreRetryLoop


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg: str):
        self.messages.append(msg)


def _make_instance(monkeypatch, *, n_attempts, n_accepted, instance_cost, reviews, config_values):
    # Create instance without calling __init__
    inst = object.__new__(ScoreRetryLoop)
    # set attributes expected by retry
    inst._reviews = reviews
    inst.logger = DummyLogger()
    inst._config = SimpleNamespace(**config_values)

    # Monkeypatch properties on the class for this test instance
    monkeypatch.setattr(ScoreRetryLoop, "_n_attempts", property(lambda self: n_attempts))
    monkeypatch.setattr(ScoreRetryLoop, "_n_accepted", property(lambda self: n_accepted))
    monkeypatch.setattr(ScoreRetryLoop, "_total_stats", property(lambda self: SimpleNamespace(instance_cost=instance_cost)))
    return inst


def test_retry_exits_on_cost_limit(monkeypatch):
    # cost limit smaller than instance cost -> immediate exit
    reviews = [SimpleNamespace(accept=0.1), SimpleNamespace(accept=0.5)]
    cfg = {"cost_limit": 100, "max_attempts": 10, "max_accepts": 5, "min_budget_for_new_attempt": 1}
    inst = _make_instance(monkeypatch,
                          n_attempts=1,
                          n_accepted=0,
                          instance_cost=200,
                          reviews=reviews,
                          config_values=cfg)

    result = inst.retry()
    assert result is False
    # logger should have one message mentioning cost limit exceeded
    assert len(inst.logger.messages) == 1
    assert "exceeds cost limit" in inst.logger.messages[0]
    # ensure stat string contains n_samples and max_score computed from reviews
    assert "n_samples=1" in inst.logger.messages[0]
    assert "max_score=" in inst.logger.messages[0]


def test_retry_exits_on_max_attempts(monkeypatch):
    # attempts reached -> exit
    reviews = []
    cfg = {"cost_limit": 1000, "max_attempts": 5, "max_accepts": 5, "min_budget_for_new_attempt": 1}
    inst = _make_instance(monkeypatch,
                          n_attempts=5,
                          n_accepted=0,
                          instance_cost=10,
                          reviews=reviews,
                          config_values=cfg)

    result = inst.retry()
    assert result is False
    assert len(inst.logger.messages) == 1
    assert "max_attempts" in inst.logger.messages[0]
    # With empty reviews max_score should default to -100.0 in the stat string
    assert "max_score=-100.0" in inst.logger.messages[0]


def test_retry_exits_on_max_accepts(monkeypatch):
    # accepts reached -> exit
    reviews = [SimpleNamespace(accept=0.9)]
    cfg = {"cost_limit": 1000, "max_attempts": 10, "max_accepts": 2, "min_budget_for_new_attempt": 1}
    inst = _make_instance(monkeypatch,
                          n_attempts=1,
                          n_accepted=2,
                          instance_cost=10,
                          reviews=reviews,
                          config_values=cfg)

    result = inst.retry()
    assert result is False
    assert len(inst.logger.messages) == 1
    assert "max_accepts" in inst.logger.messages[0]
    # check stat string values present
    assert "n_accepted=2" in inst.logger.messages[0]


def test_retry_exits_on_insufficient_budget_for_new_attempt(monkeypatch):
    # remaining budget smaller than min_budget_for_new_attempt -> exit
    reviews = [SimpleNamespace(accept=0.2)]
    cfg = {"cost_limit": 100, "max_attempts": 10, "max_accepts": 10, "min_budget_for_new_attempt": 10}
    # instance_cost leaves remaining_budget = 5 < 10
    inst = _make_instance(monkeypatch,
                          n_attempts=1,
                          n_accepted=0,
                          instance_cost=95,
                          reviews=reviews,
                          config_values=cfg)

    result = inst.retry()
    assert result is False
    assert len(inst.logger.messages) == 1
    assert "Not enough budget left for a new attempt" in inst.logger.messages[0]
    # ensure remaining values are in the message
    assert "(5 remaining" in inst.logger.messages[0]


def test_retry_all_checks_pass_returns_true(monkeypatch):
    # All limits allow another attempt -> return True
    reviews = [SimpleNamespace(accept=0.3), SimpleNamespace(accept=0.8)]
    cfg = {"cost_limit": 1000, "max_attempts": 10, "max_accepts": 10, "min_budget_for_new_attempt": 1}
    inst = _make_instance(monkeypatch,
                          n_attempts=1,
                          n_accepted=0,
                          instance_cost=10,
                          reviews=reviews,
                          config_values=cfg)

    result = inst.retry()
    assert result is True
    # No logger messages should be appended when continuing
    assert inst.logger.messages == []
