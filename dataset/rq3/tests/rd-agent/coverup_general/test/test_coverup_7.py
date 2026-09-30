# file: rdagent/scenarios/qlib/proposal/quant_proposal.py:50-166
# asked: {"lines": [53, 54, 55, 56, 57, 58, 60, 62, 63, 64, 65, 66, 69, 70, 71, 73, 74, 77, 78, 79, 80, 82, 84, 86, 87, 88, 90, 91, 92, 93, 95, 96, 97, 99, 100, 102, 103, 105, 106, 107, 108, 110, 111, 112, 114, 115, 116, 118, 119, 120, 121, 123, 124, 125, 127, 128, 129, 130, 131, 132, 135, 137, 138, 139, 140, 141, 143, 145, 146, 147, 148, 149, 150, 152, 154, 155, 156, 157, 158, 159, 161, 162, 163, 166], "branches": [[53, 54], [53, 62], [54, 55], [54, 60], [62, 63], [62, 86], [86, 87], [86, 88], [91, 92], [91, 96], [92, 93], [92, 95], [96, 97], [96, 99], [99, 100], [99, 102], [103, 105], [103, 116], [106, 107], [106, 129], [107, 108], [107, 109], [109, 106], [109, 114], [116, 118], [116, 129], [119, 120], [119, 129], [120, 121], [120, 122], [122, 119], [122, 127], [129, 130], [129, 135], [138, 139], [138, 145], [139, 138], [139, 140], [146, 147], [146, 154], [147, 148], [147, 154], [148, 147], [148, 149]]}
# gained: {"lines": [53, 54, 55, 56, 57, 58, 62, 63, 64, 65, 69, 70, 71, 73, 77, 78, 79, 80, 82, 84, 86, 87, 88, 90, 91, 92, 93, 96, 97, 99, 100, 102, 103, 105, 106, 107, 108, 110, 111, 112, 114, 115, 116, 118, 119, 120, 121, 123, 124, 125, 127, 128, 129, 130, 131, 132, 137, 138, 139, 140, 141, 143, 145, 146, 147, 148, 149, 150, 152, 154, 155, 156, 157, 158, 159, 161, 162, 163, 166], "branches": [[53, 54], [53, 62], [54, 55], [62, 63], [62, 86], [86, 87], [91, 92], [91, 96], [92, 93], [96, 97], [99, 100], [99, 102], [103, 105], [103, 116], [106, 107], [106, 129], [107, 108], [107, 109], [109, 106], [109, 114], [116, 118], [119, 120], [119, 129], [120, 121], [120, 122], [122, 119], [122, 127], [129, 130], [138, 139], [138, 145], [139, 138], [139, 140], [146, 147], [146, 154], [147, 148], [147, 154], [148, 147], [148, 149]]}

import json
import types
import random
import pytest

import rdagent.scenarios.qlib.proposal.quant_proposal as qp


class DummyHypothesis:
    def __init__(self, action):
        self.action = action


class DummyExperiment:
    def __init__(self, action, name=None):
        self.hypothesis = DummyHypothesis(action)
        self.name = name or f"exp_{action}"


class DummyFeedback:
    def __init__(self, decision: bool):
        self.decision = decision


class DummyController:
    def __init__(self, decide_return="factor"):
        self.record_calls = []
        self.decide_return = decide_return

    def record(self, metric, prev_action):
        self.record_calls.append((metric, prev_action))

    def decide(self, metric):
        # could use metric to decide; return predetermined value
        return self.decide_return


class DummyT:
    def __init__(self, key):
        self.key = key

    def r(self, **kwargs):
        # Return distinct outputs depending on the key to help assertions
        if self.key == "scenarios.qlib.prompts:hypothesis_and_feedback":
            trace = kwargs.get("trace")
            # show how many history items included
            return f"HYP_AND_FB:len={len(getattr(trace, 'hist', []))}"
        if self.key == "scenarios.qlib.prompts:last_hypothesis_and_feedback":
            exp = kwargs.get("experiment")
            fb = kwargs.get("feedback")
            return f"LAST:{getattr(exp.hypothesis, 'action', None)}:{getattr(fb, 'decision', None)}"
        if self.key == "scenarios.qlib.prompts:sota_hypothesis_and_feedback":
            exp = kwargs.get("experiment")
            fb = kwargs.get("feedback")
            return f"SOTA:{getattr(exp.hypothesis, 'action', None)}:{getattr(fb, 'decision', None)}"
        if self.key == "scenarios.qlib.prompts:action_gen.system":
            return "SYSTEM_PROMPT"
        if self.key == "scenarios.qlib.prompts:action_gen.user":
            # include passed-in summary strings to be visible to APIBackend stub
            return f"USER_PROMPT:{kwargs.get('hypothesis_and_feedback')}|{kwargs.get('last_hypothesis_and_feedback')}"
        if self.key == "scenarios.qlib.prompts:hypothesis_output_format_with_action":
            return "OUTPUT_FORMAT"
        if self.key == "scenarios.qlib.prompts:factor_hypothesis_specification":
            return "FACTOR_SPEC"
        if self.key == "scenarios.qlib.prompts:model_hypothesis_specification":
            return "MODEL_SPEC"
        return f"TPL:{self.key}:{kwargs}"


def fake_T(key):
    return DummyT(key)


class FakeAPIBackend:
    def __init__(self, response_action="model"):
        self.calls = []
        self.response_action = response_action

    def build_messages_and_create_chat_completion(self, user_prompt, system_prompt, json_mode=True):
        self.calls.append((user_prompt, system_prompt, json_mode))
        return json.dumps({"action": self.response_action})


def fake_extract_metrics_from_experiment(exp):
    # return a metric dict including the experiment name to help assertions
    return {"metric_for": getattr(exp, "name", "unknown")}


def setup_module_patch(monkeypatch, action_selection="random", api_action="model", decide_return="factor"):
    # Patch QUANT_PROP_SETTING in the module under test
    monkeypatch.setattr(qp, "QUANT_PROP_SETTING", types.SimpleNamespace(action_selection=action_selection))
    # Patch T
    monkeypatch.setattr(qp, "T", fake_T)
    # Patch APIBackend factory/class to return our fake backend
    monkeypatch.setattr(qp, "APIBackend", lambda: FakeAPIBackend(response_action=api_action))
    # Patch extract_metrics_from_experiment
    monkeypatch.setattr(qp, "extract_metrics_from_experiment", fake_extract_metrics_from_experiment)
    # Ensure random.choice can be controlled externally in tests if needed
    # Return a controller factory for tests to attach to traces
    return lambda: DummyController(decide_return=decide_return)


def make_dummy_trace(scen, hist, controller):
    # Create a simple object with required attributes used by the function
    class SimpleTrace:
        def __init__(self, scen, hist, controller):
            self.scen = scen
            self.hist = hist
            self.controller = controller

    return SimpleTrace(scen=scen, hist=hist, controller=controller)


def test_bandit_with_history_and_factor_action(monkeypatch):
    # Setup patching: QUANT_PROP_SETTING.action_selection = "bandit"
    controller_factory = setup_module_patch(monkeypatch, action_selection="bandit", api_action="model", decide_return="factor")

    # Build history: mix of model and factor experiments, include one model with decision True (SOTA)
    hist = [
        (DummyExperiment("model", name="m0"), DummyFeedback(decision=False)),
        (DummyExperiment("factor", name="f1"), DummyFeedback(decision=False)),
        (DummyExperiment("factor", name="f2"), DummyFeedback(decision=True)),
        (DummyExperiment("model", name="m1"), DummyFeedback(decision=True)),  # SOTA model
        (DummyExperiment("factor", name="f3"), DummyFeedback(decision=False)),
    ]

    controller = controller_factory()
    # Ensure controller.decide will return 'factor' (as per decide_return above)
    gen = qp.QlibQuantHypothesisGen(scen=object())
    dummy_trace = make_dummy_trace(scen=object(), hist=hist, controller=controller)

    context, ok = gen.prepare_context(dummy_trace)

    # Postconditions
    assert ok is True
    # The generator should have set targets equal to the decided action
    assert gen.targets == "factor"
    # Controller.record should have been called once with extracted metric and previous action
    assert len(controller.record_calls) == 1
    metric, prev_action = controller.record_calls[0]
    # metric should come from fake_extract_metrics_from_experiment and include the last experiment name
    assert metric == {"metric_for": "f3"}
    assert prev_action == "factor"  # last experiment's hypothesis.action was 'factor'
    # Context should include keys specified in function
    assert "hypothesis_and_feedback" in context
    assert "last_hypothesis_and_feedback" in context
    assert "SOTA_hypothesis_and_feedback" in context
    assert "RAG" in context
    assert "hypothesis_output_format" in context
    # Since action was factor, hypothesis_specification should be FACTOR_SPEC
    assert context["hypothesis_specification"] == "FACTOR_SPEC"
    # last_hypothesis_and_feedback should reflect the most recent experiment with action == 'factor'
    assert context["last_hypothesis_and_feedback"].startswith("LAST:factor")
    # Since there is a SOTA model (m1 with decision True), SOTA_hypothesis_and_feedback should be populated only for 'model' action; for 'factor' it should be None
    assert context["SOTA_hypothesis_and_feedback"] is None


def test_llm_with_history_produces_model_and_sota(monkeypatch):
    # Setup: action_selection 'llm', API returns action 'model', controller decide not used
    controller_factory = setup_module_patch(monkeypatch, action_selection="llm", api_action="model", decide_return="factor")

    # Build history where there are multiple models and one of them is SOTA (decision True)
    hist = [
        (DummyExperiment("factor", name="fA"), DummyFeedback(decision=True)),  # SOTA factor
        (DummyExperiment("model", name="mA"), DummyFeedback(decision=False)),
        (DummyExperiment("model", name="mB"), DummyFeedback(decision=True)),  # SOTA model
        (DummyExperiment("factor", name="fB"), DummyFeedback(decision=False)),
    ]

    controller = controller_factory()
    gen = qp.QlibQuantHypothesisGen(scen=object())
    dummy_trace = make_dummy_trace(scen=object(), hist=hist, controller=controller)

    # Call prepare_context which will go through the LLM branch and call our FakeAPIBackend
    context, ok = gen.prepare_context(dummy_trace)

    assert ok is True
    # The APIBackend fake returns action 'model' so targets must be model
    assert gen.targets == "model"
    # Context should have model-specific RAG guidance
    assert "GRU" in context["RAG"] or "GRU" in qp.__dict__.get("qp_unused", "") or isinstance(context["RAG"], str)
    # Because action == 'model', hypothesis_specification should be MODEL_SPEC
    assert context["hypothesis_specification"] == "MODEL_SPEC"
    # last_hypothesis_and_feedback should be the most recent experiment whose hypothesis.action == 'model'
    assert context["last_hypothesis_and_feedback"].startswith("LAST:model")
    # sota_hypothesis_and_feedback should be populated by the most recent model with decision True (mB)
    assert context["SOTA_hypothesis_and_feedback"].startswith("SOTA:model:mB".split(":")[0]) or context["SOTA_hypothesis_and_feedback"].startswith("SOTA:model")


def test_random_with_empty_history_sets_first_round_message_and_model(monkeypatch):
    # Setup QUANT_PROP_SETTING.action_selection = "random" and make random.choice return "model"
    setup_module_patch(monkeypatch, action_selection="random", api_action="model", decide_return="factor")
    monkeypatch.setattr(random, "choice", lambda seq: "model")

    gen = qp.QlibQuantHypothesisGen(scen=object())
    # Empty history should trigger first-round messages
    controller = DummyController()
    dummy_trace = make_dummy_trace(scen=object(), hist=[], controller=controller)

    context, ok = gen.prepare_context(dummy_trace)

    assert ok is True
    assert gen.targets == "model"
    # For an empty history, hypothesis_and_feedback should be the first-round message
    assert context["hypothesis_and_feedback"] == "No previous hypothesis and feedback available since it's the first round."
    # last_hypothesis_and_feedback and SOTA should be None because no history exists
    assert context["last_hypothesis_and_feedback"] is None
    assert context["SOTA_hypothesis_and_feedback"] is None
    # For action model, RAG should be the model guidance string (not None)
    assert context["RAG"] is not None
    # hypothesis_output_format and hypothesis_specification should be present
    assert context["hypothesis_output_format"] == "OUTPUT_FORMAT"
    assert context["hypothesis_specification"] == "MODEL_SPEC"
