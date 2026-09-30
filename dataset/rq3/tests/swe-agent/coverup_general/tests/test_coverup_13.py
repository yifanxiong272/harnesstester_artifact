# file: sweagent/agent/agents.py:895-963
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 935, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 955, 956, 958, 959, 961], "branches": [[929, 930], [929, 935], [954, 955], [957, 958], [960, 961]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 935, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 955, 956, 958, 959, 961], "branches": [[929, 930], [929, 935], [954, 955], [957, 958], [960, 961]]}

import time
import pytest
from types import SimpleNamespace

from sweagent.agent.agents import (
    DefaultAgent,
    RETRY_WITH_OUTPUT_TOKEN,
    RETRY_WITHOUT_OUTPUT_TOKEN,
    EXIT_FORFEIT_TOKEN,
    _RetryWithOutput,
    _RetryWithoutOutput,
    _ExitForfeit,
)
from swerex.exceptions import CommandTimeoutError
from sweagent.types import StepOutput


def make_agent(templates=None, tools=None, model=None):
    # Minimal required constructor args
    if templates is None:
        templates = SimpleNamespace(command_cancelled_timeout_template="{{command}} {{timeout}}")
    if tools is None:
        cfg = SimpleNamespace(execution_timeout=1, max_consecutive_execution_timeouts=2)
        tools = SimpleNamespace(
            should_block_action=lambda action: False,
            guard_multiline_input=lambda a: a,
            get_state=lambda env: {"ok": True},
            config=cfg,
            check_for_submission_cmd=lambda obs: False,  # required by handle_submission
        )
    else:
        # ensure check_for_submission_cmd exists
        if not hasattr(tools, "check_for_submission_cmd"):
            tools.check_for_submission_cmd = lambda obs: False

    if model is None:
        model = SimpleNamespace()

    agent = DefaultAgent(
        templates=templates,
        tools=tools,
        history_processors=[],
        model=model,
    )

    # minimal chook
    agent._chook = SimpleNamespace(
        on_action_started=lambda step: None,
        on_action_executed=lambda step: None,
    )

    # simple logger that records calls
    class DummyLogger:
        def __init__(self):
            self.critical_called = False
            self.exception_called = False
            self.info_called = False
            self.last_critical_msg = None
            self.last_exception_args = None

        def critical(self, msg, *args, **kwargs):
            self.critical_called = True
            self.last_critical_msg = msg

        def exception(self, *args, **kwargs):
            self.exception_called = True
            self.last_exception_args = args

        def info(self, *args, **kwargs):
            self.info_called = True

    agent.logger = DummyLogger()

    # ensure format dict is simple and deterministic for template rendering
    agent._get_format_dict = lambda **kwargs: {}

    return agent


def test_timeout_exceeds_max_raises_and_updates_time():
    agent = make_agent()
    max_timeouts = agent.tools.config.max_consecutive_execution_timeouts
    # env that raises CommandTimeoutError on communicate
    class Env:
        def communicate(self, input, timeout, check):
            raise CommandTimeoutError("timeout")

        def interrupt_session(self):
            # should not be reached in this test (we raise before calling it)
            raise AssertionError("interrupt should not be called")

    agent._env = Env()
    # set counters so that incrementing will hit the max and trigger immediate exit
    agent._n_consecutive_timeouts = max_timeouts - 1
    step = StepOutput(action="ls")
    start_total = agent._total_execution_time
    with pytest.raises(CommandTimeoutError):
        agent.handle_action(step)
    # _n_consecutive_timeouts should be incremented to max
    assert agent._n_consecutive_timeouts == max_timeouts
    # total execution time should have increased and step.execution_time should be set
    assert agent._total_execution_time >= start_total
    assert step.execution_time > 0
    assert agent.logger.critical_called is True
    assert "Exiting agent due to too many consecutive execution timeouts" in agent.logger.last_critical_msg


def test_interrupt_session_exception_propagates_and_updates_time():
    agent = make_agent()
    # env that raises CommandTimeoutError on communicate and interrupt_session raises
    class Env:
        def communicate(self, input, timeout, check):
            raise CommandTimeoutError("timeout")

        def interrupt_session(self):
            raise ValueError("interrupt failed")

    agent._env = Env()
    agent._n_consecutive_timeouts = 0
    step = StepOutput(action="echo hi")
    start_total = agent._total_execution_time
    with pytest.raises(ValueError):
        agent.handle_action(step)
    # consecutive timeouts incremented
    assert agent._n_consecutive_timeouts == 1
    # total execution time updated and step.execution_time set
    assert agent._total_execution_time >= start_total
    assert step.execution_time > 0
    # logger.exception should have been called
    assert agent.logger.exception_called is True


def test_successful_timeout_sets_observation_template_and_updates_counters():
    # Test path where communicate times out but interrupt_session succeeds and observation is set via template
    templates = SimpleNamespace(command_cancelled_timeout_template="CANCEL {{timeout}} {{command}}")
    agent = make_agent(templates=templates)
    class Env:
        def communicate(self, input, timeout, check):
            raise CommandTimeoutError("timeout")

        def interrupt_session(self):
            # succeed
            return None

    agent._env = Env()
    agent._n_consecutive_timeouts = 0
    # ensure execution timeout value is known
    agent.tools.config.execution_timeout = 1
    step = StepOutput(action="ls")
    start_total = agent._total_execution_time
    # Should not raise because max_consecutive_execution_timeouts is 2 and this will be first timeout
    result = agent.handle_action(step)
    # After handling, observation should be rendered template
    assert "CANCEL" in step.observation
    # Template should include timeout and command (command uses the run_action which is guarded and stripped)
    assert step.observation.strip() == f"CANCEL {agent.tools.config.execution_timeout} {step.action}"
    # counters updated
    assert agent._n_consecutive_timeouts == 1
    assert agent._total_execution_time >= start_total
    assert step.execution_time > 0
    # handle_action returns a (possibly copied) step with same content
    assert result.dict() == step.dict()


@pytest.mark.parametrize(
    "token, expected_exception, expect_replaced",
    [
        (RETRY_WITH_OUTPUT_TOKEN, _RetryWithOutput, True),
        (RETRY_WITHOUT_OUTPUT_TOKEN, _RetryWithoutOutput, True),
        (EXIT_FORFEIT_TOKEN, _ExitForfeit, False),
    ],
)
def test_retry_and_exit_tokens_raise_and_modify_observation(token, expected_exception, expect_replaced):
    agent = make_agent()
    # env that returns observation containing the token
    class Env:
        def communicate(self, input, timeout, check):
            return f"before{token}after"

        def interrupt_session(self):
            return None

    agent._env = Env()
    agent._n_consecutive_timeouts = 0
    step = StepOutput(action="pwd")
    with pytest.raises(expected_exception):
        agent.handle_action(step)
    if expect_replaced:
        assert step.observation == "beforeafter"
    else:
        # EXIT_FORFEIT should not modify the observation before raising
        assert token in step.observation
