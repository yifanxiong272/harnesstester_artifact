# file: sweagent/agent/reviewer.py:593-595
# asked: {"lines": [595], "branches": []}
# gained: {"lines": [595], "branches": []}

import builtins
import types
import pytest

from sweagent.agent.reviewer import ScoreRetryLoop


class DummyReview:
    def __init__(self, accept):
        self.accept = accept


class DummyConfig:
    def __init__(self, accept_score):
        self.accept_score = accept_score


def make_loop_with_reviews(reviews, accept_score):
    # Create instance without running __init__
    loop = object.__new__(ScoreRetryLoop)
    # Attach only the attributes needed by the _n_accepted property
    loop._reviews = reviews
    loop._config = DummyConfig(accept_score)
    return loop


def test_n_accepted_counts_threshold_inclusive():
    reviews = [DummyReview(0.2), DummyReview(0.8), DummyReview(0.5)]
    loop = make_loop_with_reviews(reviews, accept_score=0.5)
    # 0.8 and 0.5 are >= 0.5, so expect 2
    assert loop._n_accepted == 2
    assert isinstance(loop._n_accepted, int)


def test_n_accepted_empty_list_returns_zero():
    loop = make_loop_with_reviews([], accept_score=0.1)
    assert loop._n_accepted == 0


def test_n_accepted_all_below_threshold():
    reviews = [DummyReview(-1), DummyReview(0.0), DummyReview(0.0999)]
    loop = make_loop_with_reviews(reviews, accept_score=0.1)
    assert loop._n_accepted == 0
