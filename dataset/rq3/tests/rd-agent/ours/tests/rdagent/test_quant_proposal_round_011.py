import json
import types
from types import SimpleNamespace
import pytest

import rdagent.scenarios.qlib.proposal.quant_proposal as qp


class DummyTObj:
    def __init__(self, key):
        self.key = key

    def r(self, **kwargs):
        # Return deterministically based on the template key
        if self.key.endswith("hypothesis_output_format_with_action"):
            return "OUTPUT_FMT"
        if self.key.endswith("model_hypothesis_specification"):
            return "MODEL_SPEC"
        if self.key.endswith("factor_hypothesis_specification"):
            return "FACTOR_SPEC"
        if self.key.endswith("hypothesis_and_feedback"):
            return "HYP_FEED"
        if self.key.endswith("last_hypothesis_and_feedback"):
            return "LAST_HF"
        if self.key.endswith("sota_hypothesis_and_feedback"):
            return "SOTA"
        if self.key.endswith("action_gen.system"):
            return "SYS_PROMPT"
        if self.key.endswith("action_gen.user"):
            # ensure it echoes passed in kwargs so we can assert it was constructed
            return f"USER_PROMPT|{sorted(kwargs.keys())}"
        # fallback
        return f"T({self.key})"


class DummyAPIBackend:
    def build_messages_and_create_chat_completion(self, user_prompt, system_prompt, json_mode=False):
        # ensure signature matches call site; return JSON string
        # The test will set this to return predictable action
        return json.dumps(self._resp)


class FakeController:
    def __init__(self, decide_return):
        self.decide_return = decide_return
        self.record_calls = []

    def record(self, metric, prev_action):
        self.record_calls.append((metric, prev_action))

    def decide(self, metric):
        return self.decide_return


class FakeExperiment:
    def __init__(self, action):
        self.hypothesis = SimpleNamespace(action=action)


class FakeFeedback:
    def __init__(self, decision):
        self.decision = decision


class FakeTrace:
    def __init__(self, scen=None):
        self.scen = scen
        self.hist = []
        # controller may or may not be set by tests
        self.controller = None


@pytest.fixture(autouse=True)
def patch_T_and_API_and_extract(monkeypatch):
    # Patch T factory, APIBackend, and extract_metrics to deterministic fakes in module under test
    monkeypatch.setattr(qp, "T", lambda key: DummyTObj(key))
    dummy_api = DummyAPIBackend()
    monkeypatch.setattr(qp, "APIBackend", lambda: dummy_api)

    # default extract metrics returns fixed metric object
    monkeypatch.setattr(qp, "extract_metrics_from_experiment", lambda exp: {"metric": "m", "val": 1})
    return dummy_api


def test_bandit_round_011(patch_T_and_API_and_extract, monkeypatch):
    # Arrange: set action selection to bandit and create a trace with one historical experiment
    class QS: pass
    qs = QS()
    qs.action_selection = "bandit"
    monkeypatch.setattr(qp, "QUANT_PROP_SETTING", qs)

    gen = qp.QlibQuantHypothesisGen(None)

    trace = FakeTrace()
    # last experiment has hypothesis.action 'factor' (prev_action), controller will decide 'model'
    exp = FakeExperiment(action="factor")
    fb = FakeFeedback(decision=True)
    trace.hist = [(exp, fb)]

    controller = FakeController(decide_return="model")
    trace.controller = controller

    # Act
    ctx, ok = gen.prepare_context(trace)

    # Assert: controller.record was called with extracted metric and prev_action
    assert controller.record_calls, "controller.record should have been called"
    recorded_metric, recorded_prev = controller.record_calls[-1]
    assert recorded_metric == {"metric": "m", "val": 1}
    assert recorded_prev == "factor"

    # target set on instance
    assert gen.targets == "model"
    assert ok is True

    # hypothesis_specification for model path should use MODEL_SPEC
    assert ctx["hypothesis_specification"] == "MODEL_SPEC"
    # hypothesis_output_format should be present
    assert ctx["hypothesis_output_format"] == "OUTPUT_FMT"


def test_llm_round_011(patch_T_and_API_and_extract, monkeypatch):
    # Arrange: set selection to llm and an empty trace
    class QS: pass
    qs = QS()
    qs.action_selection = "llm"
    monkeypatch.setattr(qp, "QUANT_PROP_SETTING", qs)

    # configure APIBackend to return JSON with action 'factor'
    api_inst = patch_T_and_API_and_extract
    api_inst._resp = {"action": "factor"}

    gen = qp.QlibQuantHypothesisGen(None)
    trace = FakeTrace()
    trace.hist = []

    # Act
    ctx, ok = gen.prepare_context(trace)

    # Assert deterministic results for empty history
    assert ok is True
    assert gen.targets == "factor"

    # With no history, hypothesis_and_feedback downgraded to the default string
    assert ctx["hypothesis_and_feedback"] == "No previous hypothesis and feedback available since it's the first round."

    # RAG for 'factor' when history length < 6
    assert isinstance(ctx["RAG"], str)
    assert "easiest and fastest factors" in ctx["RAG"]

    # hypothesis_specification should be the factor spec
    assert ctx["hypothesis_specification"] == "FACTOR_SPEC"


def test_random_model_trace_selection_round_011(patch_T_and_API_and_extract, monkeypatch):
    # Arrange: set selection to random and make random.choice return 'model'
    class QS: pass
    qs = QS()
    qs.action_selection = "random"
    monkeypatch.setattr(qp, "QUANT_PROP_SETTING", qs)

    monkeypatch.setattr(qp.random, "choice", lambda seq: "model")

    gen = qp.QlibQuantHypothesisGen(None)

    # build a trace with interleaved model and factor experiments and some decisions
    trace = FakeTrace()
    # Older entries first -> hist[0] oldest, hist[-1] newest
    e1 = FakeExperiment("factor")
    f1 = FakeFeedback(decision=True)   # eligible factor to insert
    e2 = FakeExperiment("model")
    f2 = FakeFeedback(decision=False)
    e3 = FakeExperiment("factor")
    f3 = FakeFeedback(decision=False)
    e4 = FakeExperiment("model")
    f4 = FakeFeedback(decision=True)

    trace.hist = [(e1, f1), (e2, f2), (e3, f3), (e4, f4)]

    # Act
    ctx, ok = gen.prepare_context(trace)

    # Assert
    assert ok is True
    # The random choice forced model path
    assert gen.targets == "model"

    # The code should call T(...).r for hypothesis_and_feedback (we return HYP_FEED)
    assert ctx["hypothesis_and_feedback"] == "HYP_FEED"

    # last_hypothesis_and_feedback should be set to LAST_HF because loop finds last model
    assert ctx["last_hypothesis_and_feedback"] == "LAST_HF"

    # since there is a model with decision True (e4,f4), SOTA should be set
    assert ctx["SOTA_hypothesis_and_feedback"] == "SOTA"

    # model spec expected
    assert ctx["hypothesis_specification"] == "MODEL_SPEC"
