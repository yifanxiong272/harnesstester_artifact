import pytest
from types import SimpleNamespace

from sweagent.agent.reviewer import ScoreRetryLoop


def test_review_model_stats_returns_stats_round_141():
    # Create an instance without running __init__ to avoid complex constructor requirements
    inst = object.__new__(ScoreRetryLoop)

    # Provide a simple model object that has a `stats` attribute
    stats_obj = {"attempts": 3, "accepted": 1}
    inst._model = SimpleNamespace(stats=stats_obj)

    # The property should return the exact stats object stored on the model
    returned = inst.review_model_stats
    assert returned is stats_obj
    assert returned["attempts"] == 3
    assert returned["accepted"] == 1


def test_review_model_stats_reflects_updates_round_141():
    # Ensure the property reflects later updates to the model.stats attribute
    inst = object.__new__(ScoreRetryLoop)

    first = {"score": 0.1}
    inst._model = SimpleNamespace(stats=first)
    assert inst.review_model_stats is first

    # Replace the stats object on the model and ensure the property reflects the change
    second = {"score": 0.9}
    inst._model.stats = second
    assert inst.review_model_stats is second
    assert inst.review_model_stats["score"] == 0.9


def test_review_model_stats_missing_stats_raises_round_141():
    # If the underlying model does not have a `stats` attribute, accessing the property should raise
    inst = object.__new__(ScoreRetryLoop)
    inst._model = SimpleNamespace()  # no stats attribute

    with pytest.raises(AttributeError):
        _ = inst.review_model_stats
