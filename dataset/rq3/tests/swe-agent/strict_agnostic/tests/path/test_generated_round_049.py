import types
import numpy as np
import pytest

from sweagent.agent.reviewer import ScoreRetryLoop


class DummyLogger:
    def debug(self, *args, **kwargs):
        # deterministic no-op logger for tests
        pass

    def info(self, *args, **kwargs):
        # deterministic no-op logger for tests
        pass


def make_loop_with_state(reviews, submissions):
    """Create a ScoreRetryLoop instance without calling its real __init__.

    We only need the attributes used by get_best: _reviews, _submissions, logger.
    """
    loop = object.__new__(ScoreRetryLoop)
    loop._reviews = reviews
    loop._submissions = submissions
    loop.logger = DummyLogger()
    return loop


def test_get_best_empty_round_049():
    """When there are no reviews, get_best should return None (branch 648->649).

    This covers the branch where len(self._reviews) == 0.
    """
    loop = make_loop_with_state(reviews=[], submissions=[])
    assert loop.get_best() is None


def test_get_best_single_round_049():
    """Single review should return index 0 (branch 648->650 path, basic path).

    - One review with an accept score should pick index 0.
    """
    # One review with accept score 0.42
    r0 = types.SimpleNamespace(accept=0.42)
    # corresponding submission must have model_stats.api_calls (any truthy int works)
    s0 = types.SimpleNamespace(model_stats=types.SimpleNamespace(api_calls=1))

    loop = make_loop_with_state(reviews=[r0], submissions=[s0])
    result = loop.get_best()
    assert isinstance(result, int)
    assert result == 0


def test_get_best_tie_breaker_round_049():
    """When multiple reviews tie on score, choose the submission with the smallest api_calls.

    This exercises the tie-handling and sorting by model_stats.api_calls (lines 652-656).
    It also verifies that None api_calls are treated as infinity (float('inf')).
    """
    # Two reviews with identical accept scores (tie)
    score = 0.9
    r0 = types.SimpleNamespace(accept=score)
    r1 = types.SimpleNamespace(accept=score)
    r2 = types.SimpleNamespace(accept=0.5)  # lower score, should not be chosen

    # Submissions: r0 has api_calls None (treated as inf), r1 has 5 calls, r2 has 2 calls
    s0 = types.SimpleNamespace(model_stats=types.SimpleNamespace(api_calls=None))
    s1 = types.SimpleNamespace(model_stats=types.SimpleNamespace(api_calls=5))
    s2 = types.SimpleNamespace(model_stats=types.SimpleNamespace(api_calls=2))

    loop = make_loop_with_state(reviews=[r0, r1, r2], submissions=[s0, s1, s2])

    chosen = loop.get_best()

    # r0 and r1 tie on score; since r0.api_calls is None -> treated as inf, r1 has 5
    # r1 should be preferred over r0. r2 has lower score and should not be selected.
    assert chosen == 1
