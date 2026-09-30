import logging
from types import SimpleNamespace
import pytest

from sweagent.agent.agents import (
    DefaultAgent,
    ContentPolicyViolationError,
    BashIncorrectSyntaxError,
    CommandTimeoutError,
    TotalCostLimitExceededError,
    RetryError,
    SwerexException,
    _RetryWithOutput,
    _RetryWithoutOutput,
    _ExitForfeit,
    _TotalExecutionTimeExceeded,
)
from sweagent.types import StepOutput


def make_agent_stub():
    # Create a DefaultAgent instance without running its real __init__
    agent = object.__new__(DefaultAgent)
    agent.logger = logging.getLogger("test_agent")
    agent.max_requeries = 3
    # templates and tools minimal config
    agent.templates = SimpleNamespace(
        shell_check_error_template="shell_template",
        next_step_template="next_template",
    )
    agent.tools = SimpleNamespace(
        config=SimpleNamespace(
            format_error_template="format_template",
            filter=SimpleNamespace(blocklist_error_template="blocklist_template"),
        )
    )
    # Trajectory and counters
    agent._trajectory = []

    def add_step_to_trajectory(step):
        agent._trajectory.append(step)

    agent.add_step_to_trajectory = add_step_to_trajectory

    # Default implementations that tests will override or inspect
    agent.get_model_requery_history_calls = []

    def get_model_requery_history(**kwargs):
        agent.get_model_requery_history_calls.append(kwargs)
        # Default requery returns a history list that would be suitable
        return [{"role": "assistant", "content": "requery"}]

    agent.get_model_requery_history = get_model_requery_history

    agent.attempt_autosubmission_after_error_calls = []

    def attempt_autosubmission_after_error(step_output):
        agent.attempt_autosubmission_after_error_calls.append(step_output)
        # Return the StepOutput passed through so tests can assert on it
        return step_output

    agent.attempt_autosubmission_after_error = attempt_autosubmission_after_error

    return agent


def seq_forward_behavior(agent, behaviors):
    """Return a forward function that performs behaviors sequentially.
    behaviors is an iterable of either Exceptions to raise or StepOutput to return.
    """
    it = iter(behaviors)
    calls = {"count": 0}

    def forward(history):
        calls["count"] += 1
        val = next(it)
        if isinstance(val, Exception):
            raise val
        return val

    return forward, calls


def test_content_policy_resample_round_021():
    agent = make_agent_stub()
    # First call raises ContentPolicyViolationError, second returns a StepOutput
    out = StepOutput(thought="ok", exit_status="0", output="ok", done=False)
    forward, calls = seq_forward_behavior(agent, [ContentPolicyViolationError("blocked"), out])
    agent.forward = forward

    res = agent.forward_with_handling([])
    assert res is out
    assert calls["count"] == 2


def test_bash_syntax_triggers_requery_round_021():
    agent = make_agent_stub()
    sentinel = StepOutput(thought="after_bash", exit_status="0", output="ok", done=False)
    # forward: first raises BashIncorrectSyntaxError, second returns sentinel
    exc = BashIncorrectSyntaxError("bad bash")
    forward, calls = seq_forward_behavior(agent, [exc, sentinel])
    agent.forward = forward

    # Keep track of get_model_requery_history calls
    agent.get_model_requery_history_calls.clear()

    res = agent.forward_with_handling([])
    assert res is sentinel
    # Ensure requery was requested with the shell check template
    assert any(
        call.get("error_template") == agent.templates.shell_check_error_template
        for call in agent.get_model_requery_history_calls
    )


def test_retry_with_output_uses_next_step_template_round_021():
    agent = make_agent_stub()
    sentinel = StepOutput(thought="next", exit_status="0", output="ok", done=False)
    exc = _RetryWithOutput("need output")
    forward, calls = seq_forward_behavior(agent, [exc, sentinel])
    agent.forward = forward

    agent.get_model_requery_history_calls.clear()
    res = agent.forward_with_handling([])
    assert res is sentinel
    assert any(call.get("error_template") == agent.templates.next_step_template for call in agent.get_model_requery_history_calls)


def test_retry_without_output_passes_round_021():
    agent = make_agent_stub()
    sentinel = StepOutput(thought="ok", exit_status="0", output="ok", done=False)
    exc = _RetryWithoutOutput()
    forward, calls = seq_forward_behavior(agent, [exc, sentinel])
    agent.forward = forward

    # Should not call get_model_requery_history for _RetryWithoutOutput
    agent.get_model_requery_history_calls.clear()
    res = agent.forward_with_handling([])
    assert res is sentinel
    assert agent.get_model_requery_history_calls == []


def test_exit_forfeit_calls_autosubmit_round_021():
    agent = make_agent_stub()
    exc = _ExitForfeit()
    # forward raises forfeit
    def forward(history):
        raise exc

    agent.forward = forward
    # attempt_autosubmission_after_error returns its argument; call forward_with_handling -> should return StepOutput created in handler
    out = agent.forward_with_handling([])
    # The attempt_autosubmission_after_error should have been called once
    assert len(agent.attempt_autosubmission_after_error_calls) == 1
    called = agent.attempt_autosubmission_after_error_calls[0]
    assert isinstance(called, StepOutput)
    assert called.exit_status == "exit_forfeit"
    assert out is called


def test_total_execution_time_exceeded_autosubmit_round_021():
    agent = make_agent_stub()

    def forward(history):
        raise _TotalExecutionTimeExceeded()

    agent.forward = forward
    res = agent.forward_with_handling([])
    assert len(agent.attempt_autosubmission_after_error_calls) == 1
    called = agent.attempt_autosubmission_after_error_calls[0]
    assert isinstance(called, StepOutput)
    assert called.exit_status == "exit_total_execution_time"
    assert res is called


def test_command_timeout_autosubmit_round_021():
    agent = make_agent_stub()

    def forward(history):
        raise CommandTimeoutError("timeout")

    agent.forward = forward
    res = agent.forward_with_handling([])
    assert len(agent.attempt_autosubmission_after_error_calls) == 1
    called = agent.attempt_autosubmission_after_error_calls[0]
    assert isinstance(called, StepOutput)
    assert called.exit_status == "exit_command_timeout"


def test_total_cost_limit_re_raised_round_021():
    agent = make_agent_stub()

    def forward(history):
        raise TotalCostLimitExceededError("costy")

    agent.forward = forward
    # This exception should be re-raised by forward_with_handling
    with pytest.raises(TotalCostLimitExceededError):
        agent.forward_with_handling([])


def test_retry_error_triggers_api_autosubmit_round_021():
    agent = make_agent_stub()

    def forward(history):
        # tenacity.RetryError typically wraps an exception; string content should appear in message
        raise RetryError(Exception("underlying"))

    agent.forward = forward
    res = agent.forward_with_handling([])
    assert len(agent.attempt_autosubmission_after_error_calls) == 1
    called = agent.attempt_autosubmission_after_error_calls[0]
    assert isinstance(called, StepOutput)
    assert called.exit_status == "exit_api"
    assert "underlying" in called.output or "underlying" in called.thought


def test_swerex_runtime_and_generic_error_autosubmit_round_021():
    # Test SwerexException
    agent = make_agent_stub()

    def forward_swerex(history):
        raise SwerexException("envfail")

    agent.forward = forward_swerex
    res = agent.forward_with_handling([])
    assert agent.attempt_autosubmission_after_error_calls
    last = agent.attempt_autosubmission_after_error_calls[-1]
    assert last.exit_status == "exit_environment_error"

    # Test RuntimeError
    agent2 = make_agent_stub()

    def forward_runtime(history):
        raise RuntimeError("runtime fail")

    agent2.forward = forward_runtime
    res2 = agent2.forward_with_handling([])
    assert agent2.attempt_autosubmission_after_error_calls
    last2 = agent2.attempt_autosubmission_after_error_calls[-1]
    assert last2.exit_status == "exit_error"
    assert "runtime" in last2.output or "runtime" in last2.thought

    # Test generic Exception
    agent3 = make_agent_stub()

    def forward_generic(history):
        raise Exception("unknown fail")

    agent3.forward = forward_generic
    res3 = agent3.forward_with_handling([])
    assert agent3.attempt_autosubmission_after_error_calls
    last3 = agent3.attempt_autosubmission_after_error_calls[-1]
    assert last3.exit_status == "exit_error"
    assert "unknown fail" in last3.output or "unknown fail" in last3.thought


def test_keyboard_interrupt_propagates_round_021():
    agent = make_agent_stub()

    def forward(history):
        raise KeyboardInterrupt()

    agent.forward = forward
    with pytest.raises(KeyboardInterrupt):
        agent.forward_with_handling([])
