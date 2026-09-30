import pytest

from sweagent.agent.reviewer import get_retry_loop_from_config


class DummyConfig:
    """Simple stand-in for a real RetryLoopConfig that records the call
    and returns a deterministic sentinel value."""

    def __init__(self):
        self.called = False
        self.kwargs = None

    def get_retry_loop(self, *, problem_statement):
        # record that we were invoked and the exact kwarg passed
        self.called = True
        self.kwargs = {"problem_statement": problem_statement}
        # return a deterministic structure so callers can assert identity
        return {"sentinel": True, "problem_statement": problem_statement}


def test_get_retry_loop_calls_method_round_145():
    cfg = DummyConfig()
    ps = object()

    result = get_retry_loop_from_config(cfg, problem_statement=ps)

    # The config method must have been invoked and given the exact object
    assert cfg.called is True
    assert cfg.kwargs is not None
    assert cfg.kwargs["problem_statement"] is ps

    # The returned value should be exactly what the config provided
    assert isinstance(result, dict)
    assert result.get("sentinel") is True
    assert result.get("problem_statement") is ps


def test_get_retry_loop_propagates_exception_round_145():
    class BadConfig:
        def get_retry_loop(self, *, problem_statement):
            raise RuntimeError("simulated-failure")

    with pytest.raises(RuntimeError, match="simulated-failure"):
        get_retry_loop_from_config(BadConfig(), problem_statement=None)
