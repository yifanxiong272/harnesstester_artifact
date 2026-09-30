# file: rdagent/components/coder/factor_coder/eva_utils.py:479-550
# asked: {"lines": [487, 489, 490, 491, 494, 496, 497, 498, 499, 500, 502, 503, 504, 508, 509, 510, 512, 514, 516, 519, 520, 521, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 535, 536, 538, 539, 541, 542, 543, 544, 545, 546, 547, 548, 550], "branches": [[496, 497], [496, 519], [507, 514], [507, 516], [523, 524], [523, 550], [545, 523], [545, 546]]}
# gained: {"lines": [487, 489, 490, 491, 494, 496, 497, 498, 499, 500, 502, 503, 504, 508, 509, 510, 512, 514, 516, 519, 520, 521, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 535, 536, 538, 539, 541, 542, 543, 544, 545, 546, 547, 548], "branches": [[496, 497], [507, 514], [507, 516], [523, 524], [545, 523], [545, 546]]}

import importlib
import json
import pytest


def make_dummy_prompt():
    class DummyPrompt:
        def __init__(self, name):
            self.name = name

        def r(self, **kwargs):
            # return a string that includes the name and kwargs for debugging/inspection
            return f"{self.name}|{json.dumps(kwargs, default=str)}"

    def T(name):
        return DummyPrompt(name)

    return T


def make_dummy_task():
    class DummyTask:
        def get_task_information(self):
            return "dummy_task_info"

    return DummyTask()


def make_dummy_scenario():
    class DummyScenario:
        def get_scenario_all_desc(self, target_task, filtered_tag="feature"):
            return f"scenario_desc_for_{filtered_tag}"

    return DummyScenario()


def test_evaluate_success_trimming_and_value_feedback_none(monkeypatch):
    # Import module and class
    mod = importlib.import_module("rdagent.components.coder.factor_coder.eva_utils")
    FactorFinalDecisionEvaluator = getattr(mod, "FactorFinalDecisionEvaluator")

    # Monkeypatch T
    monkeypatch.setattr(mod, "T", make_dummy_prompt())

    # Build APIBackend that forces trimming on first token check then allows on second;
    # returns valid JSON for chat completion.
    class DummyAPIBackend:
        chat_token_limit = 50
        build_token_calls = 0
        create_chat_calls = 0

        def __init__(self, use_chat_cache=True):
            self.use_chat_cache = use_chat_cache

        def build_messages_and_calculate_token(self, user_prompt, system_prompt):
            # first call returns too large, subsequent calls are within limit
            DummyAPIBackend.build_token_calls += 1
            if DummyAPIBackend.build_token_calls == 1:
                return DummyAPIBackend.chat_token_limit + 10
            return DummyAPIBackend.chat_token_limit - 1

        def build_messages_and_create_chat_completion(self, **kwargs):
            DummyAPIBackend.create_chat_calls += 1
            # return a JSON string that will parse to include expected keys
            return json.dumps({"final_decision": "True", "final_feedback": "All good"})

    monkeypatch.setattr(mod, "APIBackend", DummyAPIBackend)

    # Prepare evaluator instance without calling its __init__
    evaluator = object.__new__(FactorFinalDecisionEvaluator)
    evaluator.scen = make_dummy_scenario()

    target_task = make_dummy_task()
    # Provide a long execution_feedback to ensure trimming has an effect
    execution_feedback = "x" * 200
    value_feedback = None  # should trigger the "No Ground Truth..." text branch
    code_feedback = "code ok"

    result = evaluator.evaluate(
        target_task=target_task,
        execution_feedback=execution_feedback,
        value_feedback=value_feedback,
        code_feedback=code_feedback,
    )

    # Assert it returned boolean True and the feedback string
    assert isinstance(result, tuple) and len(result) == 2
    final_decision, final_feedback = result
    assert final_decision is True
    assert final_feedback == "All good"

    # Verify that the token building was called at least twice (trimming happened)
    assert DummyAPIBackend.build_token_calls >= 2
    # And that the chat completion was invoked once
    assert DummyAPIBackend.create_chat_calls == 1


def test_evaluate_raises_value_error_on_json_decode(monkeypatch):
    mod = importlib.import_module("rdagent.components.coder.factor_coder.eva_utils")
    FactorFinalDecisionEvaluator = getattr(mod, "FactorFinalDecisionEvaluator")

    monkeypatch.setattr(mod, "T", make_dummy_prompt())

    class DummyAPIBackendBadJSON:
        chat_token_limit = 100

        def __init__(self, use_chat_cache=True):
            self.use_chat_cache = use_chat_cache

        def build_messages_and_calculate_token(self, user_prompt, system_prompt):
            return self.chat_token_limit - 1

        def build_messages_and_create_chat_completion(self, **kwargs):
            # return invalid JSON to trigger JSONDecodeError inside json.loads
            return "this is not json!!!"

    monkeypatch.setattr(mod, "APIBackend", DummyAPIBackendBadJSON)

    evaluator = object.__new__(FactorFinalDecisionEvaluator)
    evaluator.scen = None  # test branch where scen is None -> use "No scenario description."

    target_task = make_dummy_task()
    with pytest.raises(ValueError) as excinfo:
        evaluator.evaluate(
            target_task=target_task,
            execution_feedback="exec feedback",
            value_feedback="some value",
            code_feedback="code feedback",
        )

    assert "Failed to decode JSON response from API." in str(excinfo.value)


def test_evaluate_raises_key_error_after_retries(monkeypatch):
    mod = importlib.import_module("rdagent.components.coder.factor_coder.eva_utils")
    FactorFinalDecisionEvaluator = getattr(mod, "FactorFinalDecisionEvaluator")

    monkeypatch.setattr(mod, "T", make_dummy_prompt())

    class DummyAPIBackendMissingKeys:
        chat_token_limit = 100
        create_calls = 0

        def __init__(self, use_chat_cache=True):
            self.use_chat_cache = use_chat_cache

        def build_messages_and_calculate_token(self, user_prompt, system_prompt):
            return self.chat_token_limit - 1

        def build_messages_and_create_chat_completion(self, **kwargs):
            # Always return a JSON that lacks the required keys to trigger KeyError
            DummyAPIBackendMissingKeys.create_calls += 1
            return json.dumps({"unexpected_key": "no final decision here"})

    monkeypatch.setattr(mod, "APIBackend", DummyAPIBackendMissingKeys)

    evaluator = object.__new__(FactorFinalDecisionEvaluator)
    evaluator.scen = make_dummy_scenario()

    target_task = make_dummy_task()
    with pytest.raises(KeyError) as excinfo:
        evaluator.evaluate(
            target_task=target_task,
            execution_feedback="exec feedback",
            value_feedback="value provided",
            code_feedback="code feedback",
        )

    msg = str(excinfo.value)
    assert "Response from API is missing 'final_decision' or 'final_feedback' key after multiple attempts." in msg
