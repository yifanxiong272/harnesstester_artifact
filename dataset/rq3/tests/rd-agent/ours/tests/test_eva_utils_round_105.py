import json
import pytest

from rdagent.components.coder.factor_coder import eva_utils


class DummyTask:
    def get_task_information(self):
        return "dummy-task-info"


class FakeT:
    """Callable template factory replacement. Returns an object with r(...) that renders a string.
    This mirrors the shape used by eva_utils: T("...").r(...)
    """

    def __call__(self, *args, **kwargs):
        return self

    def r(self, **kwargs):
        # Return a deterministic string containing provided kwargs for easier debugging
        return "rendered_prompt:" + ";".join(f"{k}={v}" for k, v in sorted(kwargs.items()))


class FakeAPIBackend:
    """Fake APIBackend that can be configured per-test by setting the two lists below.
    - _calc_sequence: list of ints returned sequentially by build_messages_and_calculate_token
    - _create_responses: list of strings returned sequentially by build_messages_and_create_chat_completion

    Instances are lightweight; class-level lists are used so new instances in the code under test
    see the same sequences.
    """

    chat_token_limit = 1000
    _calc_sequence = []
    _create_responses = []

    def __init__(self, use_chat_cache: bool = True):
        # Accept the same parameter signature as real APIBackend
        self.use_chat_cache = use_chat_cache

    def build_messages_and_calculate_token(self, user_prompt, system_prompt):
        if FakeAPIBackend._calc_sequence:
            return FakeAPIBackend._calc_sequence.pop(0)
        # default small value
        return 0

    def build_messages_and_create_chat_completion(self, user_prompt, system_prompt, json_mode, seed, json_target_type):
        if FakeAPIBackend._create_responses:
            return FakeAPIBackend._create_responses.pop(0)
        return json.dumps({"final_decision": "false", "final_feedback": "default"})


def setup_monkeypatched_env(monkeypatch, calc_seq=None, create_responses=None):
    # Reset and install fakes in the target module
    FakeAPIBackend._calc_sequence = list(calc_seq or [])
    FakeAPIBackend._create_responses = list(create_responses or [])
    monkeypatch.setattr(eva_utils, "APIBackend", FakeAPIBackend)
    monkeypatch.setattr(eva_utils, "T", FakeT())


def test_success_first_attempt_round_105(monkeypatch):
    """When token count is under the limit and API returns valid JSON, evaluation should return parsed result."""
    setup_monkeypatched_env(
        monkeypatch,
        calc_seq=[500],  # <= chat_token_limit -> break immediately
        create_responses=[json.dumps({"final_decision": "1", "final_feedback": "ok"})],
    )

    evaluator = eva_utils.FactorFinalDecisionEvaluator(None)
    task = DummyTask()

    result = evaluator.evaluate(task, execution_feedback="exec", value_feedback=None, code_feedback="code")

    assert result == (True, "ok")


def test_trim_loop_then_success_round_105(monkeypatch):
    """Simulate several token-too-large iterations that trim execution feedback, then success."""
    # First two calls return > limit to exercise trimming, third call returns <= limit
    setup_monkeypatched_env(
        monkeypatch,
        calc_seq=[2000, 2000, 400],
        create_responses=[json.dumps({"final_decision": "true", "final_feedback": "trim-ok"})],
    )

    evaluator = eva_utils.FactorFinalDecisionEvaluator(None)
    task = DummyTask()

    # Provide a longer execution_feedback so slicing takes effect deterministically
    long_feedback = "x" * 64
    result = evaluator.evaluate(task, execution_feedback=long_feedback, value_feedback="val", code_feedback="code")

    assert result == (True, "trim-ok")


def test_json_decode_error_raises_round_105(monkeypatch):
    """If the API returns invalid JSON, a ValueError with decoding message should be raised."""
    setup_monkeypatched_env(
        monkeypatch,
        calc_seq=[100],
        create_responses=["not-a-json"],
    )

    evaluator = eva_utils.FactorFinalDecisionEvaluator(None)
    task = DummyTask()

    with pytest.raises(ValueError) as excinfo:
        evaluator.evaluate(task, execution_feedback="exec", value_feedback=None, code_feedback="code")

    assert "Failed to decode JSON response from API." in str(excinfo.value)


def test_missing_keys_retry_and_final_raise_round_105(monkeypatch):
    """If API returns JSON lacking expected keys repeatedly, the code retries and then raises KeyError with informative message."""
    # Provide three JSON responses missing keys to force retries up to max_attempts
    setup_monkeypatched_env(
        monkeypatch,
        calc_seq=[10, 10, 10],
        create_responses=[json.dumps({}), json.dumps({}), json.dumps({})],
    )

    evaluator = eva_utils.FactorFinalDecisionEvaluator(None)
    task = DummyTask()

    with pytest.raises(KeyError) as excinfo:
        evaluator.evaluate(task, execution_feedback="exec", value_feedback=None, code_feedback="code")

    assert "missing 'final_decision' or 'final_feedback'" in str(excinfo.value)
