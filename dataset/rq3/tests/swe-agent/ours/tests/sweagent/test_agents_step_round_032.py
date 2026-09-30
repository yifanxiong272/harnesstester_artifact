import pytest
from types import SimpleNamespace

from sweagent.agent.agents import RetryAgent
from sweagent.exceptions import TotalCostLimitExceededError


class DummyLogger:
    def __init__(self):
        self.calls = []

    def critical(self, *args, **kwargs):
        # record call arguments for assertions
        self.calls.append((args, kwargs))


class DummyAgentReturn:
    def __init__(self, return_value):
        self._return_value = return_value
        self.attempt_called_with = None

    def step(self):
        return self._return_value

    def attempt_autosubmission_after_error(self, *, step):
        # capture the step object passed in and return a deterministic sentinel
        self.attempt_called_with = step
        return {"autosubmitted": True}


class DummyAgentRaise:
    def __init__(self, exc, attempt_return={"autosubmitted": True}):
        self._exc = exc
        self._attempt_return = attempt_return
        self.attempt_called_with = None

    def step(self):
        raise self._exc

    def attempt_autosubmission_after_error(self, *, step):
        self.attempt_called_with = step
        return self._attempt_return


def make_fake_self(instance_cost, cost_limit, agent, logger=None):
    # Build a minimal fake 'self' object with the attributes used by RetryAgent.step
    cfg = SimpleNamespace(retry_loop=SimpleNamespace(cost_limit=cost_limit))
    total_stats = SimpleNamespace(instance_cost=instance_cost)
    if logger is None:
        logger = DummyLogger()
    fake = SimpleNamespace(
        _agent=agent,
        config=cfg,
        logger=logger,
        _total_instance_stats=total_stats,
    )
    return fake


def test_cost_exceeded_round_032():
    """When total instance cost exceeds 1.1 * cost_limit, autosubmit path is taken and logger.critical called with the specific message."""
    # Arrange: instance_cost > 1.1 * cost_limit
    cost_limit = 10
    instance_cost = 12  # 12 > 1.1 * 10 == 11
    sentinel_return = {"autosubmitted": True}
    agent = DummyAgentReturn(return_value={"ok": True})
    # The attempt_autosubmission_after_error will return sentinel_return
    agent.attempt_autosubmission_after_error = lambda *, step: sentinel_return
    logger = DummyLogger()
    fake = make_fake_self(instance_cost=instance_cost, cost_limit=cost_limit, agent=agent, logger=logger)

    # Act
    result = RetryAgent.step(fake)

    # Assert returned sentinel and logger recorded the critical call with expected message
    assert result is sentinel_return
    assert len(logger.calls) == 1
    msg_args, msg_kwargs = logger.calls[0]
    assert (
        "Total instance cost exceeded cost limit. This should not happen, please report this. Triggering autosubmit." 
        in msg_args[0]
    )
    # no exc_info passed in this branch
    assert msg_kwargs == {}


def test_total_cost_limit_exceeded_propagates_round_032():
    """If the underlying agent.step raises TotalCostLimitExceededError, it should be propagated."""
    cost_limit = 100
    instance_cost = 0  # well below limit so branch not taken
    agent = DummyAgentRaise(exc=TotalCostLimitExceededError())
    fake = make_fake_self(instance_cost=instance_cost, cost_limit=cost_limit, agent=agent)

    with pytest.raises(TotalCostLimitExceededError):
        RetryAgent.step(fake)


def test_general_exception_triggers_autosubmit_round_032():
    """A general exception raised by sub-agent.step should be logged with exc_info=True and trigger autosubmission."""
    cost_limit = 50
    instance_cost = 0
    # agent.step raises a generic exception
    exc = ValueError("boom")
    agent = DummyAgentRaise(exc=exc, attempt_return={"autosubmitted": True})
    logger = DummyLogger()
    fake = make_fake_self(instance_cost=instance_cost, cost_limit=cost_limit, agent=agent, logger=logger)

    result = RetryAgent.step(fake)

    # The autosubmission return value is returned
    assert result == {"autosubmitted": True}

    # Logger should have been called once with (msg, exception) and exc_info=True
    assert len(logger.calls) == 1
    (args, kwargs) = logger.calls[0]
    # first arg is the message string
    assert "Error in agent step: %s. This really shouldn't happen, please report this. Triggering autosubmit." in args[0]
    # second positional arg should be the exception instance
    assert args[1] is exc
    assert kwargs.get("exc_info") is True


def test_successful_step_round_032():
    """When sub-agent.step succeeds, its return value is forwarded unchanged."""
    cost_limit = 20
    instance_cost = 0
    expected = {"step_ok": 1}
    agent = DummyAgentReturn(return_value=expected)
    fake = make_fake_self(instance_cost=instance_cost, cost_limit=cost_limit, agent=agent)

    result = RetryAgent.step(fake)

    assert result == expected
