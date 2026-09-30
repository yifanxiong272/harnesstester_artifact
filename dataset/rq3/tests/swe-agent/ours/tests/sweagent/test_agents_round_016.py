import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from sweagent.agent import agents


class DummyTools:
    def __init__(self, execution_timeout=5, max_consecutive_execution_timeouts=3):
        self.config = SimpleNamespace(
            execution_timeout=execution_timeout,
            max_consecutive_execution_timeouts=max_consecutive_execution_timeouts,
        )

    def should_block_action(self, action):
        return False

    def guard_multiline_input(self, action: str) -> str:
        return action

    def get_state(self, env):
        return {"dummy_state": True}


class DummyHook:
    def on_action_started(self, step):
        pass

    def on_action_executed(self, step):
        pass


def make_agent(tools=None, env=None, logger=None):
    # Build a DefaultAgent instance without calling __init__ and inject only the
    # attributes used by handle_action to keep tests isolated and deterministic.
    agent = object.__new__(agents.DefaultAgent)
    agent.tools = tools or DummyTools()
    agent.logger = logger or MagicMock()
    agent._env = env
    agent._chook = DummyHook()
    agent._always_require_zero_exit_code = False
    agent.templates = SimpleNamespace(command_cancelled_timeout_template="Cancelled {{ timeout }} {{ command }}")
    agent._n_consecutive_timeouts = 0
    agent._total_execution_time = 0.0
    # helper used by template rendering
    agent._get_format_dict = lambda: {"x": 1}
    return agent


def make_step(action: str):
    return SimpleNamespace(action=action, done=False, observation=None, exit_status=None, state=None, execution_time=None)


def test_timeout_exceeds_max_round_016():
    # Arrange: configure tools so that the first timeout will hit the max limit
    tools = DummyTools(execution_timeout=1, max_consecutive_execution_timeouts=1)
    # env.communicate will raise the module CommandTimeoutError
    class Env:
        def communicate(self, input, timeout, check):
            raise agents.CommandTimeoutError("timeout")

        def interrupt_session(self):
            pass

    env = Env()
    agent = make_agent(tools=tools, env=env, logger=MagicMock())
    # start with one less than the limit so the increment triggers the exit branch
    agent._n_consecutive_timeouts = 0
    step = make_step("do_something")

    # Patch perf_counter to deterministic values
    with patch.object(agents.time, "perf_counter", side_effect=[100.0, 105.5]):
        with pytest.raises(agents.CommandTimeoutError):
            agent.handle_action(step)

    # Assert: the consecutive timeout counter reached the configured maximum
    assert agent._n_consecutive_timeouts >= tools.config.max_consecutive_execution_timeouts
    # execution time was recorded deterministically and added to total
    assert pytest.approx(step.execution_time, rel=1e-6) == 5.5
    assert pytest.approx(agent._total_execution_time, rel=1e-6) == 5.5


def test_timeout_interrupt_raises_round_016():
    # Arrange: allow retries but make interrupt_session fail with a non-CommandTimeout error
    tools = DummyTools(execution_timeout=2, max_consecutive_execution_timeouts=3)

    class Env:
        def communicate(self, input, timeout, check):
            raise agents.CommandTimeoutError("timeout")

        def interrupt_session(self):
            raise ValueError("interrupt failed")

    env = Env()
    agent = make_agent(tools=tools, env=env, logger=MagicMock())
    agent._n_consecutive_timeouts = 0
    step = make_step("do_something_else")

    with patch.object(agents.time, "perf_counter", side_effect=[0.0, 2.0]):
        with pytest.raises(ValueError):
            agent.handle_action(step)

    # The consecutive timeout counter should have incremented but not hit max
    assert agent._n_consecutive_timeouts == 1
    # execution times captured and added
    assert pytest.approx(step.execution_time, rel=1e-6) == 2.0
    assert pytest.approx(agent._total_execution_time, rel=1e-6) == 2.0


def test_retry_with_output_token_round_016():
    # Arrange: env.communicate returns an observation containing the RETRY_WITH_OUTPUT_TOKEN
    token = agents.RETRY_WITH_OUTPUT_TOKEN

    class Env:
        def communicate(self, input, timeout, check):
            return f"prefix{token}suffix"

        def interrupt_session(self):
            pass

    env = Env()
    tools = DummyTools()
    agent = make_agent(tools=tools, env=env, logger=MagicMock())
    # nonzero to ensure reset to zero in the successful path
    agent._n_consecutive_timeouts = 2
    step = make_step("some action")

    with patch.object(agents.time, "perf_counter", side_effect=[1.0, 1.25]):
        with pytest.raises(agents._RetryWithOutput):
            agent.handle_action(step)

    # The token should have been removed from the observation
    assert token not in step.observation
    assert step.observation == "prefixsuffix"
    # consecutive timeouts should have been reset on successful execution
    assert agent._n_consecutive_timeouts == 0


def test_retry_without_output_token_round_016():
    token = agents.RETRY_WITHOUT_OUTPUT_TOKEN

    class Env:
        def communicate(self, input, timeout, check):
            return f"a{token}b"

        def interrupt_session(self):
            pass

    env = Env()
    tools = DummyTools()
    agent = make_agent(tools=tools, env=env, logger=MagicMock())
    agent._n_consecutive_timeouts = 1
    step = make_step("act")

    with patch.object(agents.time, "perf_counter", side_effect=[2.0, 3.0]):
        with pytest.raises(agents._RetryWithoutOutput):
            agent.handle_action(step)

    # token removed
    assert token not in step.observation
    assert step.observation == "ab"
    assert agent._n_consecutive_timeouts == 0


def test_exit_forfeit_token_round_016():
    token = agents.EXIT_FORFEIT_TOKEN

    class Env:
        def communicate(self, input, timeout, check):
            return f"will forfeit {token} now"

        def interrupt_session(self):
            pass

    env = Env()
    tools = DummyTools()
    agent = make_agent(tools=tools, env=env, logger=MagicMock())
    step = make_step("act")

    with patch.object(agents.time, "perf_counter", side_effect=[0.0, 0.1]):
        with pytest.raises(agents._ExitForfeit):
            agent.handle_action(step)

    # For EXIT_FORFEIT_TOKEN the code raises without replacing the token
    assert token in step.observation
