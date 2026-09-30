import pytest

from sweagent.agent.agents import RetryAgent


class _FakeEnv:
    def __init__(self):
        self.hard_reset_called = 0

    def hard_reset(self):
        # deterministic side effect to observe call
        self.hard_reset_called += 1


def test_next_attempt_increments_and_resets_round_081():
    """When _env is present, _next_attempt should increment _i_attempt, call env.hard_reset(), and call _setup_agent()."""
    # create instance without running __init__ to avoid complex constructor requirements
    agent = object.__new__(RetryAgent)

    # initial attempt counter
    agent._i_attempt = 0

    # attach fake env
    fake_env = _FakeEnv()
    agent._env = fake_env

    # record if _setup_agent is called
    called = {
        "setup": 0
    }

    def fake_setup_agent():
        called["setup"] += 1

    # patch the method the unit calls
    agent._setup_agent = fake_setup_agent

    # exercise
    agent._next_attempt()

    # assertions: _i_attempt incremented, hard_reset called exactly once, _setup_agent called
    assert agent._i_attempt == 1
    assert fake_env.hard_reset_called == 1
    assert called["setup"] == 1


def test_next_attempt_asserts_when_no_env_round_081():
    """When _env is explicitly None, _next_attempt should raise an AssertionError and not change _i_attempt."""
    agent = object.__new__(RetryAgent)

    # set a sentinel attempt count
    agent._i_attempt = 5

    # explicitly set env to None to trigger the assertion
    agent._env = None

    # patch _setup_agent to something that would fail if called (should not be called)
    def failing_setup():
        raise RuntimeError("_setup_agent should not be called when env is None")

    agent._setup_agent = failing_setup

    with pytest.raises(AssertionError):
        agent._next_attempt()

    # ensure attempt count not changed due to the assertion happening first
    assert agent._i_attempt == 5
