# file: sweagent/agent/agents.py:895-963
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 935, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 955, 956, 958, 959, 961], "branches": [[929, 930], [929, 935], [954, 955], [957, 958], [960, 961]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 935, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 955, 956, 958, 959, 961], "branches": [[929, 930], [929, 935], [954, 955], [957, 958], [960, 961]]}

import types
import pytest

from types import SimpleNamespace

import sweagent.agent.agents as agents_mod
from swerex.exceptions import CommandTimeoutError


class DummyEnv:
    def __init__(self, *, communicate_result=None, communicate_exc=None, interrupt_exc=None):
        self._communicate_result = communicate_result
        self._communicate_exc = communicate_exc
        self._interrupt_exc = interrupt_exc
        self.interrupted = False
        self.communicated_with = None

    def communicate(self, *, input, timeout, check):
        self.communicated_with = dict(input=input, timeout=timeout, check=check)
        if self._communicate_exc:
            raise self._communicate_exc
        return self._communicate_result

    def interrupt_session(self):
        self.interrupted = True
        if self._interrupt_exc:
            raise self._interrupt_exc
        return None


class DummyTools:
    def __init__(self, *, execution_timeout=5, max_consecutive_execution_timeouts=3):
        self.config = SimpleNamespace(
            execution_timeout=execution_timeout,
            max_consecutive_execution_timeouts=max_consecutive_execution_timeouts,
            parse_function=None,
        )
        # defaults:
        self._should_block = False

    def should_block_action(self, action):
        return self._should_block

    def guard_multiline_input(self, action):
        return action

    def get_state(self, env):
        return {"dummy_state": True}


class DummyCHook:
    def on_action_started(self, step):
        pass

    def on_action_executed(self, step):
        pass


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.criticals = []
        self.exceptions = []

    def info(self, *args, **kwargs):
        self.infos.append((args, kwargs))

    def critical(self, *args, **kwargs):
        self.criticals.append((args, kwargs))

    def exception(self, *args, **kwargs):
        self.exceptions.append((args, kwargs))


class StepObj:
    def __init__(self, action):
        self.action = action
        self.observation = ""
        self.done = False
        self.exit_status = None
        self.state = None
        self.execution_time = None


def make_agent_instance():
    # Create a DefaultAgent instance without invoking __init__
    agent = agents_mod.DefaultAgent.__new__(agents_mod.DefaultAgent)
    agent._catch_errors = True
    agent._always_require_zero_exit_code = False
    agent.name = "test"
    agent.model = None
    agent.templates = SimpleNamespace(command_cancelled_timeout_template="Cancelled {{ timeout }} {{ command }}")
    agent.tools = DummyTools()
    agent.history_processors = []
    agent.max_requeries = 3
    agent.logger = DummyLogger()
    agent._env = None
    agent._problem_statement = None
    agent.traj_path = None
    agent.history = []
    agent._trajectory = []
    agent.info = SimpleNamespace()
    agent._chook = DummyCHook()
    agent._replay_config = None
    agent._action_sampler = None
    agent._n_consecutive_timeouts = 0
    agent._total_execution_time = 0.0

    # Provide a simple _get_format_dict so template render works even if implementation expects more keys.
    agent._get_format_dict = types.MethodType(lambda self, **kwargs: {}, agent)

    return agent


def make_perf_counter_sequence(values):
    it = iter(values)

    def _pc():
        try:
            return next(it)
        except StopIteration:
            # If exhausted, return last known value
            return values[-1]

    return _pc


def test_timeout_exceeding_max_increments_and_raises(monkeypatch):
    agent = make_agent_instance()
    # set up tools config
    agent.tools = DummyTools(execution_timeout=10, max_consecutive_execution_timeouts=3)
    # set initial consecutive timeouts to max-1 so that increment will reach max and trigger raise
    agent._n_consecutive_timeouts = 2

    # env that raises CommandTimeoutError when communicating
    env = DummyEnv(communicate_exc=CommandTimeoutError("timeout"))
    agent._env = env

    step = StepObj(action="do something")
    # make time deterministic: start 1.0, end 3.0 -> exec time 2.0
    monkeypatch.setattr(agents_mod.time, "perf_counter", make_perf_counter_sequence([1.0, 3.0]))

    with pytest.raises(CommandTimeoutError):
        agent.handle_action(step)

    # After raise, consecutive timeouts should have incremented to 3 (the max)
    assert agent._n_consecutive_timeouts == 3
    # execution_time should be set on the step and total updated
    assert step.execution_time == pytest.approx(2.0)
    assert agent._total_execution_time == pytest.approx(2.0)


def test_timeout_interrupt_raises_and_logs_exception(monkeypatch):
    agent = make_agent_instance()
    agent.tools = DummyTools(execution_timeout=7, max_consecutive_execution_timeouts=5)
    agent._n_consecutive_timeouts = 0

    # env.communicate raises timeout, interrupt_session raises an exception
    env = DummyEnv(communicate_exc=CommandTimeoutError("timeout"), interrupt_exc=RuntimeError("interrupt failed"))
    agent._env = env

    step = StepObj(action="another action")
    # time: start 0.0 end 1.5 => exec time 1.5
    monkeypatch.setattr(agents_mod.time, "perf_counter", make_perf_counter_sequence([0.0, 1.5]))

    # Because interrupt_session raises, the code re-raises that interrupt exception.
    with pytest.raises(RuntimeError):
        agent.handle_action(step)

    # n_consecutive_timeouts incremented by 1
    assert agent._n_consecutive_timeouts == 1
    # total execution time updated
    assert agent._total_execution_time == pytest.approx(1.5)
    # logger.exception should have been called once
    assert len(agent.logger.exceptions) >= 1
    # step.execution_time should be set
    assert step.execution_time == pytest.approx(1.5)


def test_timeout_interrupt_success_sets_observation_and_continues(monkeypatch):
    agent = make_agent_instance()
    agent.tools = DummyTools(execution_timeout=42, max_consecutive_execution_timeouts=5)
    agent._n_consecutive_timeouts = 0

    # env.communicate raises timeout; interrupt_session succeeds
    env = DummyEnv(communicate_exc=CommandTimeoutError("timeout"), interrupt_exc=None)
    agent._env = env

    step = StepObj(action="ls -la")
    # deterministic time: start 10.0, finish 10.6 => exec 0.6
    monkeypatch.setattr(agents_mod.time, "perf_counter", make_perf_counter_sequence([10.0, 10.6]))

    # Prevent handle_submission from trying to call model_copy by stubbing it out
    agent.handle_submission = types.MethodType(lambda self, step, **kwargs: step, agent)

    out = agent.handle_action(step)

    # No exception, step returned
    assert out is step
    expected = "Cancelled 42 ls -la"
    # observation should be rendered from template with timeout and command inserted
    assert step.observation == expected
    # total execution time updated appropriately
    assert agent._total_execution_time == pytest.approx(0.6)
    assert step.execution_time == pytest.approx(0.6)
    # state should be set via tools.get_state
    assert step.state == {"dummy_state": True}


@pytest.mark.parametrize(
    "token, exception_type, expect_removed",
    [
        (agents_mod.RETRY_WITH_OUTPUT_TOKEN, agents_mod._RetryWithOutput, True),
        (agents_mod.RETRY_WITHOUT_OUTPUT_TOKEN, agents_mod._RetryWithoutOutput, True),
        (agents_mod.EXIT_FORFEIT_TOKEN, agents_mod._ExitForfeit, False),
    ],
)
def test_observation_tokens_raise_control_exceptions(token, exception_type, expect_removed):
    agent = make_agent_instance()
    agent.tools = DummyTools()
    # env that returns observation containing the token
    agent._env = DummyEnv(communicate_result=f"prefix{token}suffix")
    step = StepObj(action="echo hi")
    # no timing manipulation needed; let real perf_counter run briefly
    with pytest.raises(exception_type):
        agent.handle_action(step)
    # token should have been removed from observation for the first two tokens only
    if expect_removed:
        assert token not in step.observation
    else:
        # for EXIT_FORFEIT_TOKEN the implementation raises without replacing the observation
        assert token in step.observation
