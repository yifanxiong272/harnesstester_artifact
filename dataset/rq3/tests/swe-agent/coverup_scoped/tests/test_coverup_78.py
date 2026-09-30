# file: sweagent/agent/reviewer.py:581-583
# asked: {"lines": [583], "branches": []}
# gained: {"lines": [583], "branches": []}

import types
import pytest

def test_review_model_stats_returns_model_stats(monkeypatch):
    # Import inside test to ensure monkeypatching works on the module object loaded by import
    from sweagent.agent import reviewer as reviewer_mod
    from sweagent.agent.reviewer import ScoreRetryLoop

    # Prepare a dummy model with a distinct stats object
    stats_obj = object()
    dummy_model = types.SimpleNamespace(stats=stats_obj)

    # Monkeypatch get_model used in ScoreRetryLoop.__init__
    def fake_get_model(model_config, tools=None):
        # ensure the passed config is what we set on the config below
        assert model_config == "fake_model_config"
        return dummy_model

    monkeypatch.setattr(reviewer_mod, "get_model", fake_get_model)

    # Create a minimal config object with required attributes accessed by __init__
    class DummyReviewerConfig:
        def get_reviewer(self, model):
            # Ensure the model passed in is the same dummy_model returned by fake_get_model
            assert model is dummy_model
            return "dummy_reviewer"

    config = types.SimpleNamespace(
        model="fake_model_config",
        reviewer_config=DummyReviewerConfig(),
        accept_score=0.5,
        max_accepts=1,
        max_attempts=1,
        min_budget_for_new_attempt=0.0,
        cost_limit=1.0,
    )

    # Instantiate ScoreRetryLoop; this will call our fake_get_model
    loop = ScoreRetryLoop(config, problem_statement=None)

    # Access the property that should return the underlying model.stats (line 583)
    returned = loop.review_model_stats

    # Verify that it is exactly the stats object we provided
    assert returned is stats_obj
