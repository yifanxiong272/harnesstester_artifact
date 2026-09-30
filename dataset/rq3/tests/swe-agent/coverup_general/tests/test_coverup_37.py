# file: sweagent/agent/agents.py:297-318
# asked: {"lines": [301, 305, 306, 307, 308, 309, 310, 311, 313, 314, 315, 316, 317, 318], "branches": [[305, 306], [305, 309]]}
# gained: {"lines": [301, 305, 306, 307, 308, 309, 310, 311, 313, 314, 315, 316, 317, 318], "branches": [[305, 306], [305, 309]]}

import types
import pytest

from sweagent.agent.agents import RetryAgent
from sweagent.agent.models import InstanceStats
from sweagent.exceptions import TotalCostLimitExceededError
from sweagent.types import StepOutput


class DummyLogger:
    def __init__(self):
        self.calls = []

    def critical(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class DummyAgent:
    def __init__(self, step_side_effect=None, autosubmit_return=None):
        # step_side_effect can be an exception instance to raise, or a callable returning a value, or a value
        self._step_side_effect = step_side_effect
        self._autosubmit_return = autosubmit_return
        self.attempt_called_with = None

    def step(self):
        if isinstance(self._step_side_effect, Exception):
            raise self._step_side_effect
        if callable(self._step_side_effect):
            return self._step_side_effect()
        return self._step_side_effect

    def attempt_autosubmission_after_error(self, step):
        # record that we were called and return the configured return value
        self.attempt_called_with = step
        return self._autosubmit_return


def make_retry_agent_with_state(total_instance_cost, agent: DummyAgent, cost_limit=100, logger=None):
    """
    Create a RetryAgent instance without running its __init__, then set the minimal attributes
    needed for .step() to run through the branches we want to test.

    The RetryAgent._total_instance_stats property returns self._total_instance_attempt_stats + self._rloop.review_model_stats,
    so we set those two to produce the desired total_instance_cost.
    """
    ra = object.__new__(RetryAgent)
    # config needs a retry_loop.cost_limit attribute; create a simple namespace that will be used directly
    ra.config = types.SimpleNamespace(retry_loop=types.SimpleNamespace(cost_limit=cost_limit))
    # set logger
    ra.logger = logger or DummyLogger()
    # set _agent so the initial assert passes
    ra._agent = agent
    # set _total_instance_attempt_stats and _rloop.review_model_stats so their sum equals total_instance_cost
    # we'll put all cost in the review_model_stats
    ra._total_instance_attempt_stats = InstanceStats(instance_cost=0.0)
    ra._rloop = types.SimpleNamespace(review_model_stats=InstanceStats(instance_cost=total_instance_cost))
    return ra


def test_total_instance_cost_exceeded_triggers_autosubmit_and_logs():
    # Use cost_limit 10 -> 1.1 * 10 = 11, so set instance_cost > 11
    cost_limit = 10
    total_instance_cost = 12.0
    sentinel = object()
    dummy_agent = DummyAgent(step_side_effect=lambda: "should not be called", autosubmit_return=sentinel)
    logger = DummyLogger()
    ra = make_retry_agent_with_state(total_instance_cost, dummy_agent, cost_limit=cost_limit, logger=logger)

    result = ra.step()

    # Should have returned the autosubmit return value
    assert result is sentinel
    # Logger should have been called once with the expected message (match substring)
    assert len(logger.calls) == 1
    args, kwargs = logger.calls[0]
    assert "Total instance cost exceeded cost limit" in args[0]
    # Ensure attempt_autosubmission_after_error was called with a StepOutput instance
    assert isinstance(dummy_agent.attempt_called_with, StepOutput)


def test_total_cost_limit_exception_is_re_raised():
    # If the sub-agent raises TotalCostLimitExceededError it should propagate
    cost_limit = 100  # large so the other branch isn't triggered
    total_instance_cost = 0.0
    dummy_agent = DummyAgent(step_side_effect=TotalCostLimitExceededError("limit hit"), autosubmit_return=None)
    ra = make_retry_agent_with_state(total_instance_cost, dummy_agent, cost_limit=cost_limit)

    with pytest.raises(TotalCostLimitExceededError):
        ra.step()


def test_general_exception_triggers_autosubmit_and_logs_with_exception_info():
    # Test that a generic exception from agent.step triggers autosubmit and logger.critical called with exc_info
    cost_limit = 100
    total_instance_cost = 0.0
    sentinel = object()
    dummy_agent = DummyAgent(step_side_effect=Exception("boom"), autosubmit_return=sentinel)
    logger = DummyLogger()
    ra = make_retry_agent_with_state(total_instance_cost, dummy_agent, cost_limit=cost_limit, logger=logger)

    result = ra.step()

    # Should have called attempt_autosubmission_after_error and returned its value
    assert result is sentinel
    # Logger should have one call
    assert len(logger.calls) == 1
    args, kwargs = logger.calls[0]
    # The message should mention "Error in agent step"
    assert "Error in agent step" in args[0]
    # The exception object should be passed as the second positional argument
    assert isinstance(args[1], Exception)
    # exc_info=True should have been passed
    assert kwargs.get("exc_info") is True
    # Ensure attempt_autosubmission_after_error was called with a StepOutput instance
    assert isinstance(dummy_agent.attempt_called_with, StepOutput)
