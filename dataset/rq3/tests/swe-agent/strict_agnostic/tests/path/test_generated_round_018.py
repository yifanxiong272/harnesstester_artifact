import time
import types
import pytest
from types import SimpleNamespace
from sweagent.agent import agents
from sweagent.agent.agents import DefaultAgent

# Helper small fakes used by multiple tests
class DummyLogger:
    def __init__(self):
        self.records = {"info": [], "critical": [], "exception": []}
    def info(self, *args, **kwargs):
        self.records["info"].append((args, kwargs))
    def critical(self, *args, **kwargs):
        self.records["critical"].append((args, kwargs))
    def exception(self, *args, **kwargs):
        self.records["exception"].append((args, kwargs))

class DummyCHook:
    def __init__(self):
        self.started = False
        self.executed = False
    def on_action_started(self, step):
        self.started = True
    def on_action_executed(self, step):
        self.executed = True

class DummyTools:
    def __init__(self, max_timeouts=1, execution_timeout=2):
        self.config = SimpleNamespace(
            max_consecutive_execution_timeouts=max_timeouts,
            execution_timeout=execution_timeout,
        )
    def should_block_action(self, action):
        return False
    def guard_multiline_input(self, action):
        return action
    def get_state(self, env=None):
        return {"state": "dummy"}


def make_agent():
    # Create an instance without calling the real __init__ and inject minimal attributes
    agent = DefaultAgent.__new__(DefaultAgent)
    agent.logger = DummyLogger()
    agent._chook = DummyCHook()
    agent.templates = SimpleNamespace(command_cancelled_timeout_template="{{command}}_CANCELLED_TIMEOUT")
    agent._get_format_dict = lambda: {}
    agent._always_require_zero_exit_code = False
    agent._n_consecutive_timeouts = 0
    agent._total_execution_time = 0.0

    # default tools and env will be replaced per-test
    agent.tools = DummyTools(max_timeouts=1, execution_timeout=1)
    agent._env = None

    # stub out handle_submission to avoid deep code paths - return sentinel
    agent.handle_submission = lambda step: "HANDLED"
    return agent


def make_step(action="cmd"):
    return SimpleNamespace(
        action=action,
        observation="",
        done=False,
        exit_status=None,
        state=None,
        execution_time=0.0,
    )


def attach_env(agent, communicate_behavior=None, interrupt_behavior=None):
    class DummyEnv:
        def __init__(self, communicate_behavior, interrupt_behavior):
            self._communicate_behavior = communicate_behavior
            self._interrupt_behavior = interrupt_behavior
        def communicate(self, input=None, timeout=None, check=None):
            # behave according to provided callable (could raise or return)
            return self._communicate_behavior(input=input, timeout=timeout, check=check)
        def interrupt_session(self):
            if self._interrupt_behavior is None:
                return None
            return self._interrupt_behavior()
    agent._env = DummyEnv(communicate_behavior, interrupt_behavior)


def test_handle_action_timeout_exceed_max_round_018():
    # Simulate communicate raising CommandTimeoutError and reaching max consecutive timeouts -> re-raise
    agent = make_agent()
    # tools configured with max_timeouts == 1 so first timeout reaches the threshold
    agent.tools = DummyTools(max_timeouts=1, execution_timeout=0.1)

    # communicate raises the CommandTimeoutError as imported in the module
    def comm_raise(*, input, timeout, check):
        raise agents.CommandTimeoutError("simulated timeout")

    # interrupt_session should not be invoked in this branch (raise happens earlier)
    attach_env(agent, communicate_behavior=comm_raise, interrupt_behavior=lambda: None)

    step = make_step("some_cmd")

    with pytest.raises(agents.CommandTimeoutError):
        agent.handle_action(step)

    # After the exception, ensure we incremented count and recorded execution_time added
    assert agent._n_consecutive_timeouts >= 1
    assert agent._total_execution_time >= 0.0
    # logger should have recorded a critical log for exiting due to too many timeouts
    assert len(agent.logger.records["critical"]) >= 1


def test_handle_action_timeout_then_successful_interrupt_round_018():
    # Simulate communicate raising CommandTimeoutError, but interrupt_session succeeds -> observation set via template
    agent = make_agent()
    agent.tools = DummyTools(max_timeouts=2, execution_timeout=0.05)

    # communicate raises timeout once
    def comm_raise(*, input, timeout, check):
        raise agents.CommandTimeoutError("simulated timeout")

    # interrupt_session succeeds (no exception)
    def interrupt_ok():
        return None

    attach_env(agent, communicate_behavior=comm_raise, interrupt_behavior=interrupt_ok)

    step = make_step("my_command")

    # handle_submission returns "HANDLED" because we replaced it; handle_action should finish and return that
    result = agent.handle_action(step)
    assert result == "HANDLED"

    # The observation should have been rendered from the template with the command
    assert step.observation == "my_command_CANCELLED_TIMEOUT"

    # Ensure timeout counter incremented and total execution time increased
    assert agent._n_consecutive_timeouts >= 1
    assert agent._total_execution_time >= step.execution_time
    assert agent._chook.started is True
    assert agent._chook.executed is True


def test_handle_action_timeout_interrupt_raises_round_018():
    # Simulate communicate raising CommandTimeoutError, and interrupt_session raises an exception -> that exception propagates
    agent = make_agent()
    agent.tools = DummyTools(max_timeouts=2, execution_timeout=0.05)

    def comm_raise(*, input, timeout, check):
        raise agents.CommandTimeoutError("simulated timeout")

    def interrupt_raises():
        raise RuntimeError("interrupt failed")

    attach_env(agent, communicate_behavior=comm_raise, interrupt_behavior=interrupt_raises)

    step = make_step("x")

    with pytest.raises(RuntimeError):
        agent.handle_action(step)

    # ensure the logger recorded the exception path
    assert len(agent.logger.records["exception"]) >= 1
    # ensure execution_time got recorded before re-raising
    assert agent._total_execution_time >= 0.0


def test_handle_action_retry_tokens_and_exceptions_round_018():
    # This test covers three branches where the observation contains retry/exit tokens
    agent = make_agent()
    agent.tools = DummyTools(max_timeouts=2, execution_timeout=0.05)

    # Success communicate that returns value directly; we'll change step.observation directly after communicate
    def comm_return_retry_output(*, input, timeout, check):
        return agents.RETRY_WITH_OUTPUT_TOKEN + "output"

    attach_env(agent, communicate_behavior=comm_return_retry_output, interrupt_behavior=None)

    step = make_step("irrelevant")

    # Expect _RetryWithOutput to be raised and token removed from observation
    with pytest.raises(agents._RetryWithOutput):
        agent.handle_action(step)
    assert "RETRY_WITH_OUTPUT_TOKEN" not in step.observation

    # Now test RETRY_WITHOUT_OUTPUT_TOKEN
    def comm_return_retry_without(*, input, timeout, check):
        return agents.RETRY_WITHOUT_OUTPUT_TOKEN + "no-output"

    attach_env(agent, communicate_behavior=comm_return_retry_without, interrupt_behavior=None)
    step2 = make_step("irrelevant2")
    with pytest.raises(agents._RetryWithoutOutput):
        agent.handle_action(step2)
    assert agents.RETRY_WITHOUT_OUTPUT_TOKEN not in step2.observation

    # Now test EXIT_FORFEIT_TOKEN
    def comm_return_exit_forfeit(*, input, timeout, check):
        return agents.EXIT_FORFEIT_TOKEN + "bye"

    attach_env(agent, communicate_behavior=comm_return_exit_forfeit, interrupt_behavior=None)
    step3 = make_step("irrelevant3")
    with pytest.raises(agents._ExitForfeit):
        agent.handle_action(step3)


# The file purposely focuses on deterministic local fakes and does not call external services
