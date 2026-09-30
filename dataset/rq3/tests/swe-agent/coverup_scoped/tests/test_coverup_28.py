# file: sweagent/agent/reviewer.py:647-658
# asked: {"lines": [648, 649, 650, 651, 652, 653, 655, 656, 657, 658], "branches": [[648, 649], [648, 650]]}
# gained: {"lines": [648, 649, 650, 651, 652, 653, 655, 656, 657, 658], "branches": [[648, 649], [648, 650]]}

import builtins
import types

import pytest

from sweagent.agent.reviewer import ScoreRetryLoop


class DummyModelStats:
    def __init__(self, api_calls):
        self.api_calls = api_calls


class DummySubmission:
    def __init__(self, api_calls):
        self.model_stats = DummyModelStats(api_calls)


class DummyReview:
    def __init__(self, accept):
        self.accept = accept


class DummyLogger:
    def __init__(self):
        self.debug_messages = []
        self.info_messages = []

    def debug(self, msg):
        self.debug_messages.append(msg)

    def info(self, msg):
        self.info_messages.append(msg)


def make_instance():
    # Create instance without calling any real constructor to avoid side effects
    inst = object.__new__(ScoreRetryLoop)
    inst.logger = DummyLogger()
    return inst


def test_get_best_returns_none_for_no_reviews():
    inst = make_instance()
    inst._reviews = []
    inst._submissions = []
    result = inst.get_best()
    assert result is None
    # No info messages should be produced for empty reviews
    assert inst.logger.info_messages == []


def test_get_best_single_review_returns_zero_and_logs():
    inst = make_instance()
    inst._reviews = [DummyReview(accept=0.42)]
    inst._submissions = [DummySubmission(api_calls=5)]
    result = inst.get_best()
    assert result == 0
    # Ensure debug logged the scores and info logged the chosen index
    assert any("Scores:" in m for m in inst.logger.debug_messages)
    assert inst.logger.info_messages == ["Best submission: 0"]


def test_get_best_ties_choose_shortest_api_calls():
    inst = make_instance()
    # three reviews with equal scores
    inst._reviews = [DummyReview(accept=0.9), DummyReview(accept=0.9), DummyReview(accept=0.9)]
    # corresponding submissions with different api_calls, including None
    # index 0 -> 50 calls, index 1 -> None (treated as infinity), index 2 -> 10 calls -> should be chosen
    inst._submissions = [DummySubmission(api_calls=50), DummySubmission(api_calls=None), DummySubmission(api_calls=10)]
    result = inst.get_best()
    assert result == 2
    # Confirm logger captured the best submission message for chosen index 2
    assert inst.logger.info_messages == ["Best submission: 2"]
