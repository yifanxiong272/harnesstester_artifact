# file: sweagent/agent/agents.py:1020-1174
# asked: {"lines": [1072, 1087, 1088, 1090, 1092, 1093, 1094, 1095, 1096, 1099, 1100, 1101, 1102, 1105, 1111, 1112, 1113, 1114, 1118, 1119, 1120, 1121, 1125, 1126, 1127, 1128, 1137, 1144, 1145, 1146, 1147, 1155, 1156, 1157, 1158, 1159, 1161, 1162, 1163, 1164, 1165], "branches": []}
# gained: {"lines": [1072, 1087, 1088, 1090, 1092, 1093, 1094, 1095, 1096, 1099, 1100, 1101, 1102, 1105, 1111, 1112, 1113, 1114, 1118, 1119, 1120, 1121, 1125, 1126, 1127, 1128, 1137, 1144, 1145, 1146, 1147, 1155, 1156, 1157, 1158, 1159, 1161, 1162, 1163, 1164, 1165], "branches": []}

import pytest
from types import SimpleNamespace
import importlib

# Import the module under test
agents = importlib.import_module("sweagent.agent.agents")
DefaultAgent = agents.DefaultAgent

# Defensive: ensure all exception names used by forward_with_handling exist on the module.
# If any are missing (depending on environment), create simple placeholders.
_exception_names = {
    "FormatError",
    "_BlockedActionError",
    "ContentPolicyViolationError",
    "BashIncorrectSyntaxError",
    "_RetryWithOutput",
    "_RetryWithoutOutput",
    "_ExitForfeit",
    "_TotalExecutionTimeExceeded",
    "CommandTimeoutError",
    "ContextWindowExceededError",
    "TotalCostLimitExceededError",
    "CostLimitExceededError",
    "RetryError",
    "SwerexException",
}
for name in _exception_names:
    if not hasattr(agents, name):
        setattr(agents, name, type(name, (Exception,), {}))

# Also import StepOutput type (used by the agent)
StepOutput = getattr(importlib.import_module("sweagent.types"), "StepOutput")


class DummyLogger:
    def __init__(self):
        self.last = None

    def warning(self, *args, **kwargs):
        self.last = ("warning", args, kwargs)

    def info(self, *args, **kwargs):
        self.last = ("info", args, kwargs)

    def exception(self, *args, **kwargs):
        self.last = ("exception", args, kwargs)


def make_agent(forward_callable, *, max_requeries=3):
    """
    Create a minimal DefaultAgent-like object by bypassing __init__
    and setting only the attributes used by forward_with_handling.
    """
    agent = object.__new__(DefaultAgent)
    agent.forward = forward_callable
    agent.get_model_requery_history = lambda *a, **k: [{"role": "assistant", "content": "requery"}]
    agent.add_step_to_trajectory = lambda step: None
    # attempt_autosubmission_after_error should return the passed StepOutput
    agent.attempt_autosubmission_after_error = lambda step: step
    agent.max_requeries = max_requeries
    agent.logger = DummyLogger()
    # Minimal templates and tools objects with required attributes
    agent.templates = SimpleNamespace(shell_check_error_template="shell_template", next_step_template="next_template")
    # tools.config.format_error_template and tools.config.filter.blocklist_error_template are referenced
    tools_config = SimpleNamespace(format_error_template="format_template")
    # nested filter with blocklist_error_template
    tools_config.filter = SimpleNamespace(blocklist_error_template="blocklist_template")
    agent.tools = SimpleNamespace(config=tools_config)
    return agent


def test_keyboard_interrupt_is_reraised():
    def forward(_history):
        raise KeyboardInterrupt()

    agent = make_agent(forward)
    with pytest.raises(KeyboardInterrupt):
        agent.forward_with_handling([])


def test_content_policy_violation_leads_to_final_format_exit():
    # forward always raises ContentPolicyViolationError so we exit due to repeated format errors
    ContentPolicyViolationError = getattr(agents, "ContentPolicyViolationError")

    def forward(_history):
        raise ContentPolicyViolationError("blocked")

    # set max_requeries to 2 to hit the loop quickly
    agent = make_agent(forward, max_requeries=2)
    # ensure attempt_autosubmission_after_error returns its input (done True etc.)
    res = agent.forward_with_handling([])
    # When loop completes due to repeated errors, the handler creates a StepOutput with exit_format
    assert isinstance(res, StepOutput)
    assert res.exit_status == "exit_format"
    assert res.done is True


def test_bash_incorrect_syntax_triggers_requery_then_success():
    BashIncorrectSyntaxError = getattr(agents, "BashIncorrectSyntaxError")

    calls = {"n": 0}

    class MyErr(BashIncorrectSyntaxError):
        def __init__(self):
            super().__init__("bad bash")
            # include a step attribute to exercise handle_error_with_retry
            self.step = StepOutput(thought="t", exit_status="1", output="o", done=False)
            self.extra_info = {"extra_key": "extra_val"}

    def forward(history):
        calls["n"] += 1
        if calls["n"] == 1:
            raise MyErr()
        # on second call return success
        return StepOutput(thought="ok", exit_status="0", output="done", done=True)

    agent = make_agent(forward, max_requeries=3)
    agent.templates = SimpleNamespace(shell_check_error_template="shell_template", next_step_template="next_template")
    # make get_model_requery_history record what it was called with and return new history for resubmission
    called = {}

    def get_model_requery_history(**kwargs):
        called.update(kwargs)
        return [{"role": "assistant", "content": "patched"}]

    agent.get_model_requery_history = get_model_requery_history
    res = agent.forward_with_handling([])
    assert isinstance(res, StepOutput)
    assert res.exit_status == "0"
    # check get_model_requery_history was called with exception_message coming from exception args
    assert "exception_message" in called


def test_retry_with_output_and_without_output_branches():
    RetryWithOutput = getattr(agents, "_RetryWithOutput")
    RetryWithoutOutput = getattr(agents, "_RetryWithoutOutput")

    calls = {"n": 0}

    class RWO(RetryWithOutput):
        def __init__(self):
            super().__init__("rwo")
            self.step = StepOutput(thought="tw", exit_status="1", output="o", done=False)

    class RWo(RetryWithoutOutput):
        pass

    # Sequence: first raise RetryWithOutput, second raise RetryWithoutOutput, third return success
    def forward(history):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RWO()
        if calls["n"] == 2:
            raise RWo("no output")
        return StepOutput(thought="final", exit_status="0", output="done", done=True)

    agent = make_agent(forward, max_requeries=4)
    agent.templates = SimpleNamespace(shell_check_error_template="shell", next_step_template="nxt")
    # Ensure get_model_requery_history works
    agent.get_model_requery_history = lambda **kwargs: [{"role": "assistant", "content": f"requery-{calls['n']}"}]
    res = agent.forward_with_handling([])
    assert isinstance(res, StepOutput)
    assert res.exit_status == "0"
    assert calls["n"] == 3


def test_exit_forfeit_and_total_time_and_command_timeout_and_context_and_cost_and_retryerror_and_runtime_and_generic_exception():
    # We'll create several agents each raising different exceptions to hit each branch.
    _ExitForfeit = getattr(agents, "_ExitForfeit")
    _TotalExecutionTimeExceeded = getattr(agents, "_TotalExecutionTimeExceeded")
    CommandTimeoutError = getattr(agents, "CommandTimeoutError")
    ContextWindowExceededError = getattr(agents, "ContextWindowExceededError")
    TotalCostLimitExceededError = getattr(agents, "TotalCostLimitExceededError")
    CostLimitExceededError = getattr(agents, "CostLimitExceededError")
    RetryError = getattr(agents, "RetryError")
    SwerexException = getattr(agents, "SwerexException")

    # 1) _ExitForfeit -> autosubmit with exit_forfeit
    def f_exit_forfeit(_):
        raise _ExitForfeit("forfeit")

    agent1 = make_agent(f_exit_forfeit)
    res1 = agent1.forward_with_handling([])
    assert isinstance(res1, StepOutput)
    assert res1.exit_status == "exit_forfeit"

    # 2) _TotalExecutionTimeExceeded -> autosubmit exit_total_execution_time
    def f_total_time(_):
        raise _TotalExecutionTimeExceeded("time")

    agent2 = make_agent(f_total_time)
    res2 = agent2.forward_with_handling([])
    assert isinstance(res2, StepOutput)
    assert res2.exit_status == "exit_total_execution_time"

    # 3) CommandTimeoutError -> autosubmit exit_command_timeout
    def f_cmd_timeout(_):
        raise CommandTimeoutError("timeout")

    agent3 = make_agent(f_cmd_timeout)
    res3 = agent3.forward_with_handling([])
    assert isinstance(res3, StepOutput)
    assert res3.exit_status == "exit_command_timeout"

    # 4) ContextWindowExceededError -> autosubmit exit_context
    def f_context(_):
        raise ContextWindowExceededError("ctx")

    agent4 = make_agent(f_context)
    res4 = agent4.forward_with_handling([])
    assert isinstance(res4, StepOutput)
    assert res4.exit_status == "exit_context"

    # 5) CostLimitExceededError -> autosubmit exit_cost
    def f_cost_limit(_):
        raise CostLimitExceededError("cost")

    agent5 = make_agent(f_cost_limit)
    res5 = agent5.forward_with_handling([])
    assert isinstance(res5, StepOutput)
    assert res5.exit_status == "exit_cost"

    # 6) RetryError -> autosubmit exit_api and message contains exception
    def f_retryerr(_):
        raise RetryError("retry problem")

    agent6 = make_agent(f_retryerr)
    res6 = agent6.forward_with_handling([])
    assert isinstance(res6, StepOutput)
    assert res6.exit_status == "exit_api"
    assert "retry problem" in (res6.output or "")

    # 7) SwerexException -> autosubmit exit_environment_error
    def f_swerex(_):
        raise SwerexException("env fail")

    agent7 = make_agent(f_swerex)
    res7 = agent7.forward_with_handling([])
    assert isinstance(res7, StepOutput)
    assert res7.exit_status == "exit_environment_error"
    assert "env fail" in (res7.output or "")

    # 8) RuntimeError -> autosubmit exit_error with runtime message
    def f_runtime(_):
        raise RuntimeError("runtime bad")

    agent8 = make_agent(f_runtime)
    res8 = agent8.forward_with_handling([])
    assert isinstance(res8, StepOutput)
    assert res8.exit_status == "exit_error"
    assert "runtime bad" in (res8.output or "")

    # 9) generic Exception (not caught earlier) -> autosubmit exit_error
    def f_generic(_):
        raise ValueError("unknown bad")

    agent9 = make_agent(f_generic)
    res9 = agent9.forward_with_handling([])
    assert isinstance(res9, StepOutput)
    assert res9.exit_status == "exit_error"
    assert "unknown bad" in (res9.output or "")


def test_total_cost_limit_is_reraised():
    # This exception path re-raises the exception (not handled), so ensure it bubbles out.
    TotalCostLimitExceededError = getattr(agents, "TotalCostLimitExceededError")

    def forward(_):
        raise TotalCostLimitExceededError("total cost exceeded")

    agent = make_agent(forward)
    with pytest.raises(TotalCostLimitExceededError):
        agent.forward_with_handling([])
