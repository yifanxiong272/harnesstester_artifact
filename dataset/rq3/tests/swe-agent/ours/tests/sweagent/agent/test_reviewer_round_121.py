import pytest

from sweagent.agent import reviewer
from sweagent.agent.reviewer import ScoreRetryLoopConfig


def test___post_init_calls_validate_round_121():
    """Ensure __post_init__ invokes validate() on the instance."""
    # construct() creates a model instance without validation/initialization side-effects
    cfg = ScoreRetryLoopConfig.construct()

    called = {"flag": False}

    # Replace the validate method on the instance to observe that it's called by __post_init__
    def fake_validate():
        called["flag"] = True

    cfg.validate = fake_validate

    # Call the post-init hook which should call our fake_validate
    cfg.__post_init__()

    assert called["flag"] is True, "__post_init__ did not call validate()"


def test_get_retry_loop_returns_score_retry_loop_round_121(monkeypatch):
    """Ensure get_retry_loop calls the ScoreRetryLoop factory with (self, problem_statement)

    We monkeypatch reviewer.ScoreRetryLoop to a simple callable that records its args
    and returns a sentinel value. This avoids importing or instantiating the real
    ScoreRetryLoop while verifying the call-site behavior.
    """
    cfg = ScoreRetryLoopConfig.construct()

    problem = object()

    captured = {"called": False, "args": None}

    def fake_score_retry_loop(cfg_arg, problem_arg):
        captured["called"] = True
        captured["args"] = (cfg_arg, problem_arg)
        # return a clearly identifiable sentinel so we can assert the returned value
        return ("SENTINEL_SCORE_RETRY_LOOP", cfg_arg, problem_arg)

    # Patch the symbol where get_retry_loop resolves ScoreRetryLoop
    monkeypatch.setattr(reviewer, "ScoreRetryLoop", fake_score_retry_loop)

    result = cfg.get_retry_loop(problem)

    assert captured["called"] is True, "ScoreRetryLoop was not invoked by get_retry_loop"
    assert captured["args"][0] is cfg, "ScoreRetryLoop was not called with the config instance"
    assert captured["args"][1] is problem, "ScoreRetryLoop was not called with the problem_statement"

    # Verify the return value is the sentinel returned by our fake factory
    assert isinstance(result, tuple) and result[0] == "SENTINEL_SCORE_RETRY_LOOP"
