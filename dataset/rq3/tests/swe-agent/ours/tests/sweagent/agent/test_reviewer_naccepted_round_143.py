import types
import pytest

from sweagent.agent.reviewer import ScoreRetryLoop


class DummyReview:
    def __init__(self, accept):
        # mimic the minimal shape expected by ScoreRetryLoop._n_accepted
        self.accept = accept


def _make_loop_with_reviews(accept_score, accepts):
    """Create a ScoreRetryLoop instance without running its __init__ and
    set the minimal attributes used by the _n_accepted property.
    """
    loop = ScoreRetryLoop.__new__(ScoreRetryLoop)
    loop._config = types.SimpleNamespace(accept_score=accept_score)
    loop._reviews = [DummyReview(a) for a in accepts]
    return loop


def test_n_accepted_basic_round_143():
    # accept_score set to 0.5; reviews contain values below, equal, and above
    loop = _make_loop_with_reviews(0.5, [0.1, 0.5, 0.9])
    # expectation: 0.5 and 0.9 are >= 0.5 -> count == 2
    assert loop._n_accepted == 2


def test_n_accepted_empty_round_143():
    # no reviews should yield 0 accepted regardless of threshold
    loop = _make_loop_with_reviews(0.9, [])
    assert loop._n_accepted == 0
