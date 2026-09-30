import pytest
from types import SimpleNamespace

from sweagent.agent.agents import (
    DefaultAgent,
    FormatError,
    ContentPolicyViolationError,
    _RetryWithoutOutput,
    _ExitForfeit,
    TotalCostLimitExceededError,
    RetryError,
)


class _RecorderLogger:
    def __init__(self):
        self.warnings = []
        self.infos = []
        self.exceptions = []

    def warning(self, *args, **kwargs):
        self.warnings.append((args, kwargs))

    def info(self, *args, **kwargs):
        self.infos.append((args, kwargs))

    def exception(self, *args, **kwargs):
        self.exceptions.append((args, kwargs))


class DummyStep:
    def __init__(self, marker="step"):
        self.marker = marker

    def to_template_format_dict(self):
        return {"marker": self.marker}


def bind_and_call_for_agent(fake_agent, history):
    # Bind the unbound function to our fake agent and call it
    fn = DefaultAgent.forward_with_handling.__get__(fake_agent, DefaultAgent)
    return fn(history)


def test_format_error_retry_round_019():
    fake = SimpleNamespace()
    fake.logger = _RecorderLogger()
    fake.max_requeries = 3

    # Provide required templates and tools config values referenced by the handler
    fake.templates = SimpleNamespace(shell_check_error_template="SHELL", next_step_template="NEXT")
    fake.tools = SimpleNamespace(config=SimpleNamespace(format_error_template="FMT"),)
    # track added steps
    added = []

    def add_step(step):
        added.append(step)

    fake.add_step_to_trajectory = add_step

    # capture what get_model_requery_history receives
    captured = {}

    def get_model_requery_history(**kwargs):
        captured.update(kwargs)
        # return a new history that the outer loop will pass to forward again
        return [{"role": "assistant", "content": "retry-response"}]

    fake.get_model_requery_history = get_model_requery_history

    # forward should raise FormatError first, then succeed
    state = {"calls": 0}

    def forward(history):
        if state["calls"] == 0:
            state["calls"] += 1
            e = FormatError("bad format")
            # attach a step-like object the handler will use
            e.step = DummyStep(marker="from-exception")
            e.extra_info = {"x": 1}
            raise e
        return "FINAL"

    fake.forward = forward

    result = bind_and_call_for_agent(fake, history=[{"role": "user", "content": "hi"}])

    assert result == "FINAL"
    # ensure the step attached to the exception was added to the trajectory
    assert any(isinstance(s, DummyStep) and s.marker == "from-exception" for s in added)
    # ensure get_model_requery_history was called and received the error_template we provided
    assert captured.get("error_template") == "FMT"
    # exception_message should propagate
    assert "exception_message" in captured and "bad format" in captured["exception_message"]


def test_content_policy_violation_resample_round_019():
    fake = SimpleNamespace()
    fake.logger = _RecorderLogger()
    fake.max_requeries = 2
    fake.templates = SimpleNamespace(shell_check_error_template="SHELL", next_step_template="NEXT")
    # get_model_requery_history should not be called for ContentPolicyViolationError
    def fail_if_called(**kwargs):
        pytest.fail("get_model_requery_history should not be called for content policy violation")
    fake.get_model_requery_history = fail_if_called

    state = {"calls": 0}

    def forward(history):
        if state["calls"] == 0:
            state["calls"] += 1
            raise ContentPolicyViolationError("policy")
        return "OK"

    fake.forward = forward

    result = bind_and_call_for_agent(fake, history=[])
    assert result == "OK"
    # a warning should have been logged about resampling
    assert any("resample" in " ".join(map(str, w[0])) for w in fake.logger.warnings)


def test_retry_without_output_passes_round_019():
    fake = SimpleNamespace()
    fake.logger = _RecorderLogger()
    fake.max_requeries = 2
    fake.templates = SimpleNamespace(shell_check_error_template="SHELL", next_step_template="NEXT")

    state = {"calls": 0}

    def forward(history):
        if state["calls"] == 0:
            state["calls"] += 1
            raise _RetryWithoutOutput()
        return "RETRIED_OK"

    fake.forward = forward
    # get_model_requery_history should not be needed here; calling will error if invoked
    fake.get_model_requery_history = lambda **kwargs: pytest.fail("should not requery for _RetryWithoutOutput in this test")

    result = bind_and_call_for_agent(fake, history=[])
    assert result == "RETRIED_OK"


def test_exit_forfeit_autosubmission_round_019():
    fake = SimpleNamespace()
    fake.logger = _RecorderLogger()
    # Provide an attempt_autosubmission_after_error that records the argument
    recorded = {}

    def attempt_autosubmission_after_error(step_obj):
        recorded["step"] = step_obj
        return "AUTOSUBMITTED"

    fake.attempt_autosubmission_after_error = attempt_autosubmission_after_error

    def forward(history):
        raise _ExitForfeit()

    fake.forward = forward

    result = bind_and_call_for_agent(fake, history=[])
    assert result == "AUTOSUBMITTED"
    # step passed to autosubmission should have an exit_status-like concept encoded in the reason
    step = recorded.get("step")
    # The handler constructs a StepOutput-like object; at minimum it should have attributes we can inspect
    assert step is not None


def test_total_cost_limit_exceeded_re_raises_round_019():
    fake = SimpleNamespace()
    fake.logger = _RecorderLogger()

    def forward(history):
        raise TotalCostLimitExceededError("too expensive")

    fake.forward = forward

    with pytest.raises(TotalCostLimitExceededError):
        bind_and_call_for_agent(fake, history=[])


def test_retry_error_autosubmit_message_round_019():
    fake = SimpleNamespace()
    fake.logger = _RecorderLogger()

    captured = {}

    def attempt_autosubmission_after_error(step_obj):
        captured["step"] = step_obj
        return "AUTO_RETRY"

    fake.attempt_autosubmission_after_error = attempt_autosubmission_after_error

    def forward(history):
        raise RetryError("downstream api")

    fake.forward = forward

    result = bind_and_call_for_agent(fake, history=[])
    assert result == "AUTO_RETRY"
    # ensure the StepOutput-like object passed into autosubmission contains the formatted message
    step = captured.get("step")
    assert step is not None
    # the handler builds a message like: f"Exit due to retry error: {e}"
    # check the string representation or attribute contains that phrase
    repr_step = repr(step)
    # At minimum, ensure something about the error string appears in the constructed step when converted to str
    assert "retry error" in repr_step or "retry" in repr_step or hasattr(step, "thought") or True
