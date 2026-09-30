# file: sweagent/agent/agents.py:297-318
# asked: {"lines": [301, 305, 306, 307, 308, 309, 310, 311, 313, 314, 315, 316, 317, 318], "branches": [[305, 306], [305, 309]]}
# gained: {"lines": [301, 305, 306, 307, 308, 309, 310, 311, 313, 314, 315, 316, 317, 318], "branches": [[305, 306], [305, 309]]}

import pytest
from types import SimpleNamespace

from sweagent.agent.agents import RetryAgent
from sweagent.types import StepOutput
from sweagent.exceptions import TotalCostLimitExceededError


class DummyLogger:
    def __init__(self):
        self.calls = []

    def critical(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class FakeAgent:
    def __init__(self, step_side_effect=None, autosub_return=None):
        # step_side_effect can be:
        # - an Exception instance to be raised
        # - a callable to be called and its return used
        # - any other value to be returned directly
        self._step_side_effect = step_side_effect
        self.autosub_return = autosub_return if autosub_return is not None else StepOutput(output="autosub_default")
        self.autosub_called = False
        self.step_called = False

    def step(self):
        self.step_called = True
        if isinstance(self._step_side_effect, Exception):
            raise self._step_side_effect
        if callable(self._step_side_effect):
            return self._step_side_effect()
        return self._step_side_effect

    def attempt_autosubmission_after_error(self, step: StepOutput):
        self.autosub_called = True
        # Return whatever was configured
        return self.autosub_return


def make_retry_agent_with(attrs: dict):
    # Create instance without calling __init__ and set required attributes
    r = object.__new__(RetryAgent)
    for k, v in attrs.items():
        setattr(r, k, v)
    return r


def set_total_stats(monkeypatch, total_stats):
    # Monkeypatch the RetryAgent._total_instance_stats property to return our total_stats object
    monkeypatch.setattr(RetryAgent, "_total_instance_stats", property(lambda self: total_stats), raising=False)


def test_total_cost_exceeded_triggers_autosubmit(monkeypatch):
    # Arrange
    fake_agent = FakeAgent(autosub_return=StepOutput(output="autosub_called"))
    logger = DummyLogger()
    config = SimpleNamespace(retry_loop=SimpleNamespace(cost_limit=10))
    # _total_instance_stats should be an object with instance_cost attribute and set high to trigger branch
    total_stats = SimpleNamespace(instance_cost=12.0)

    retry = make_retry_agent_with({
        "_agent": fake_agent,
        "config": config,
        "logger": logger,
    })
    set_total_stats(monkeypatch, total_stats)

    # Act
    result = retry.step()

    # Assert
    assert fake_agent.autosub_called is True, "attempt_autosubmission_after_error should have been called"
    assert isinstance(result, StepOutput)
    assert result.output == "autosub_called"
    # Logger should have been called with the specific message
    assert any("Total instance cost exceeded cost limit" in args[0] for args, _ in logger.calls)


def test_subagent_raises_total_cost_limit_exception_propagates(monkeypatch):
    # Arrange
    exc = TotalCostLimitExceededError("limit exceeded")
    fake_agent = FakeAgent(step_side_effect=exc)
    logger = DummyLogger()
    config = SimpleNamespace(retry_loop=SimpleNamespace(cost_limit=10))
    total_stats = SimpleNamespace(instance_cost=0.0)  # do not trigger cost-exceeded branch

    retry = make_retry_agent_with({
        "_agent": fake_agent,
        "config": config,
        "logger": logger,
    })
    set_total_stats(monkeypatch, total_stats)

    # Act & Assert: the TotalCostLimitExceededError should propagate
    with pytest.raises(TotalCostLimitExceededError):
        retry.step()
    # Ensure step was attempted on the sub-agent
    assert fake_agent.step_called is True


def test_subagent_raises_generic_exception_triggers_autosubmit_and_logs(monkeypatch):
    # Arrange
    fake_agent = FakeAgent(step_side_effect=ValueError("boom"), autosub_return=StepOutput(output="autosub_after_error"))
    logger = DummyLogger()
    config = SimpleNamespace(retry_loop=SimpleNamespace(cost_limit=10))
    total_stats = SimpleNamespace(instance_cost=0.0)  # do not trigger cost-exceeded branch

    retry = make_retry_agent_with({
        "_agent": fake_agent,
        "config": config,
        "logger": logger,
    })
    set_total_stats(monkeypatch, total_stats)

    # Act
    result = retry.step()

    # Assert
    assert fake_agent.autosub_called is True, "Autosubmission should be triggered after generic exception"
    assert isinstance(result, StepOutput)
    assert result.output == "autosub_after_error"
    # Check logger recorded the critical call with exc_info=True and the exception included as a positional arg
    found = False
    for args, kwargs in logger.calls:
        if args and "Error in agent step" in args[0]:
            # second positional arg should be the exception object or exc_info set
            assert any(isinstance(a, Exception) for a in args[1:]) or kwargs.get("exc_info", False)
            found = True
    assert found, "Expected a critical log entry about 'Error in agent step'"


def test_normal_subagent_step_returns_directly(monkeypatch):
    # Arrange
    fake_agent = FakeAgent(step_side_effect=StepOutput(output="normal_step"))
    logger = DummyLogger()
    config = SimpleNamespace(retry_loop=SimpleNamespace(cost_limit=10))
    total_stats = SimpleNamespace(instance_cost=0.0)

    retry = make_retry_agent_with({
        "_agent": fake_agent,
        "config": config,
        "logger": logger,
    })
    set_total_stats(monkeypatch, total_stats)

    # Act
    result = retry.step()

    # Assert
    assert fake_agent.step_called is True
    assert isinstance(result, StepOutput)
    assert result.output == "normal_step"
