# file: rdagent/scenarios/qlib/proposal/quant_proposal.py:50-166
# asked: {"lines": [53, 54, 55, 56, 57, 58, 60, 62, 63, 64, 65, 66, 69, 70, 71, 73, 74, 77, 78, 79, 80, 82, 84, 86, 87, 88, 90, 91, 92, 93, 95, 96, 97, 99, 100, 102, 103, 105, 106, 107, 108, 110, 111, 112, 114, 115, 116, 118, 119, 120, 121, 123, 124, 125, 127, 128, 129, 130, 131, 132, 135, 137, 138, 139, 140, 141, 143, 145, 146, 147, 148, 149, 150, 152, 154, 155, 156, 157, 158, 159, 161, 162, 163, 166], "branches": [[53, 54], [53, 62], [54, 55], [54, 60], [62, 63], [62, 86], [86, 87], [86, 88], [91, 92], [91, 96], [92, 93], [92, 95], [96, 97], [96, 99], [99, 100], [99, 102], [103, 105], [103, 116], [106, 107], [106, 129], [107, 108], [107, 109], [109, 106], [109, 114], [116, 118], [116, 129], [119, 120], [119, 129], [120, 121], [120, 122], [122, 119], [122, 127], [129, 130], [129, 135], [138, 139], [138, 145], [139, 138], [139, 140], [146, 147], [146, 154], [147, 148], [147, 154], [148, 147], [148, 149]]}
# gained: {"lines": [53, 54, 55, 56, 57, 58, 60, 62, 63, 64, 65, 69, 70, 71, 73, 77, 78, 79, 80, 82, 84, 86, 87, 88, 90, 91, 92, 93, 95, 96, 97, 99, 100, 102, 103, 105, 106, 107, 108, 110, 111, 112, 114, 115, 116, 118, 119, 120, 121, 129, 130, 131, 132, 135, 137, 138, 139, 140, 141, 143, 145, 146, 147, 148, 149, 150, 152, 154, 155, 156, 157, 158, 159, 161, 162, 163, 166], "branches": [[53, 54], [53, 62], [54, 55], [54, 60], [62, 63], [62, 86], [86, 87], [91, 92], [91, 96], [92, 93], [92, 95], [96, 97], [99, 100], [99, 102], [103, 105], [103, 116], [106, 107], [106, 129], [107, 108], [107, 109], [109, 106], [109, 114], [116, 118], [119, 120], [119, 129], [120, 121], [129, 130], [129, 135], [138, 139], [138, 145], [139, 138], [139, 140], [146, 147], [146, 154], [147, 148], [148, 149]]}

import json
import types
import pytest

import rdagent.scenarios.qlib.proposal.quant_proposal as quant_mod


class FakeController:
    def __init__(self, decide_ret="factor"):
        self.record_calls = []
        self._decide_ret = decide_ret

    def record(self, metric, prev_action):
        self.record_calls.append((metric, prev_action))

    def decide(self, metric):
        return self._decide_ret


class FakeExperiment:
    def __init__(self, action_name):
        class H:
            def __init__(self, action):
                self.action = action

        self.hypothesis = H(action_name)


class FakeFeedback:
    def __init__(self, decision):
        self.decision = decision


class FakeTrace:
    def __init__(self, scen=None):
        self.scen = scen
        self.hist = []
        self.controller = FakeController()

    def __repr__(self):
        return f"<FakeTrace hist_len={len(self.hist)}>"


class TObj:
    def __init__(self, name):
        self.name = name

    def r(self, **kwargs):
        # Check specific templates first to avoid prefix collisions
        if self.name.endswith("sota_hypothesis_and_feedback"):
            exp = kwargs.get("experiment")
            fb = kwargs.get("feedback")
            return f"SOTA:{getattr(exp.hypothesis, 'action', None)}:{getattr(fb, 'decision', None)}"
        if self.name.endswith("last_hypothesis_and_feedback"):
            exp = kwargs.get("experiment")
            fb = kwargs.get("feedback")
            return f"LAST:{getattr(exp.hypothesis, 'action', None)}:{getattr(fb, 'decision', None)}"
        if self.name.endswith("hypothesis_and_feedback"):
            tr = kwargs.get("trace")
            if tr is None:
                return "No previous hypothesis and feedback available since it's the first round."
            return f"HYP_AND_FEED_TRACE_LEN={len(tr.hist)}"
        if self.name.endswith("action_gen.system"):
            return "SYSTEM_PROMPT"
        if self.name.endswith("action_gen.user"):
            return "USER_PROMPT"
        if self.name.endswith("hypothesis_output_format_with_action"):
            return "FORMAT_WITH_ACTION"
        if self.name.endswith("factor_hypothesis_specification"):
            return "FACTOR_SPEC"
        if self.name.endswith("model_hypothesis_specification"):
            return "MODEL_SPEC"
        # generic fallback
        return f"TEMPLATE:{self.name}:{kwargs}"


def fake_T(name):
    return TObj(name)


class FakeAPIBackend:
    def __init__(self, resp_json):
        self._resp = resp_json

    def build_messages_and_create_chat_completion(self, user_prompt, system_prompt, json_mode=True):
        # Return JSON string
        return self._resp


def fake_extract_metrics_from_experiment(exp):
    # Return a deterministic metric derived from experiment action name
    act = getattr(exp.hypothesis, "action", "unknown")
    return {"metric_for": act}


@pytest.fixture(autouse=True)
def patch_module(monkeypatch):
    # Patch several dependencies in the module under test
    monkeypatch.setattr(quant_mod, "T", fake_T)
    monkeypatch.setattr(quant_mod, "APIBackend", lambda: FakeAPIBackend(json.dumps({"action": "model"})))
    monkeypatch.setattr(quant_mod, "extract_metrics_from_experiment", fake_extract_metrics_from_experiment)
    # Ensure Trace in module is our FakeTrace so Trace(trace.scen) creates FakeTrace
    monkeypatch.setattr(quant_mod, "Trace", FakeTrace)
    yield


def make_quant_instance():
    # Create instance without running parent __init__
    inst = quant_mod.QlibQuantHypothesisGen.__new__(quant_mod.QlibQuantHypothesisGen)
    return inst


def test_bandit_with_empty_hist(monkeypatch):
    # Set QUANT_PROP_SETTING.action_selection == "bandit" and empty hist
    class Q:
        action_selection = "bandit"

    monkeypatch.setattr(quant_mod, "QUANT_PROP_SETTING", Q)
    inst = make_quant_instance()
    trace = FakeTrace(scen="s1")
    # empty hist
    ctx, ok = inst.prepare_context(trace)
    assert ok is True
    # action should default to "factor" when bandit and no history
    assert inst.targets == "factor"
    # For factor and len(hist) == 0, hypothesis_and_feedback should be first-round message
    assert ctx["hypothesis_and_feedback"].startswith("No previous hypothesis")
    # Since no history, last and SOTA should be None
    assert ctx["last_hypothesis_and_feedback"] is None
    assert ctx["SOTA_hypothesis_and_feedback"] is None
    # RAG for factor with len(hist) < 6
    assert "Try the easiest and fastest factors" in ctx["RAG"]
    # Hypothesis spec should be factor spec
    assert ctx["hypothesis_specification"] == "FACTOR_SPEC"
    assert ctx["hypothesis_output_format"] == "FORMAT_WITH_ACTION"


def test_bandit_with_nonempty_hist_and_model_selection(monkeypatch):
    # bandit with previous history and controller.decide returning "model"
    class Q:
        action_selection = "bandit"

    monkeypatch.setattr(quant_mod, "QUANT_PROP_SETTING", Q)
    inst = make_quant_instance()
    trace = FakeTrace(scen="s2")
    # Create history: a model experiment with decision True to be SOTA candidate
    exp_model = FakeExperiment("model")
    fb_model = FakeFeedback(decision=True)
    trace.hist.append((exp_model, fb_model))
    # set controller decide to return model
    trace.controller = FakeController(decide_ret="model")
    # call prepare_context
    ctx, ok = inst.prepare_context(trace)
    assert ok is True
    assert inst.targets == "model"
    # Since we provided a model with decision True, sota_hypothesis_and_feedback should be present
    assert ctx["SOTA_hypothesis_and_feedback"].startswith("SOTA:model:True")
    # last_hypothesis_and_feedback should reflect the last matching action (model)
    assert ctx["last_hypothesis_and_feedback"].startswith("LAST:model:True")
    # hypothesis_and_feedback for non-empty trace should be created via templates;
    assert ctx["hypothesis_and_feedback"].startswith("HYP_AND_FEED_TRACE_LEN=")
    # For model action, hypothesis_spec should be model spec
    assert ctx["hypothesis_specification"] == "MODEL_SPEC"
    # RAG for model should be the model guidance string
    assert "In Quantitative Finance" in ctx["RAG"]


def test_llm_branch_uses_api_backend_and_parses_json(monkeypatch):
    # Set QUANT_PROP_SETTING.action_selection == "llm"
    class Q:
        action_selection = "llm"

    # Create an APIBackend that returns a JSON string with action "factor"
    monkeypatch.setattr(quant_mod, "QUANT_PROP_SETTING", Q)
    monkeypatch.setattr(quant_mod, "APIBackend", lambda: FakeAPIBackend(json.dumps({"action": "factor"})))
    inst = make_quant_instance()
    trace = FakeTrace(scen="s3")
    # Add one previous experiment so hypothesis_and_feedback uses the template returning a string
    trace.hist.append((FakeExperiment("model"), FakeFeedback(decision=False)))
    # Call prepare_context
    ctx, ok = inst.prepare_context(trace)
    assert ok is True
    # action parsed from APIBackend response should be "factor"
    assert inst.targets == "factor"
    # Because action is factor and len(hist) < 6, RAG should be the 'easiest and fastest' suggestion
    assert "Try the easiest and fastest factors" in ctx["RAG"]
    # last_hypothesis_and_feedback should be None because there is no previous 'factor' action
    assert ctx["last_hypothesis_and_feedback"] is None


def test_random_branch_and_specific_trace_selection(monkeypatch):
    # Ensure random.choice returns 'factor' deterministically
    monkeypatch.setattr(quant_mod, "random", types.SimpleNamespace(choice=lambda lst: "factor"))
    class Q:
        action_selection = "random"

    monkeypatch.setattr(quant_mod, "QUANT_PROP_SETTING", Q)
    inst = make_quant_instance()
    trace = FakeTrace(scen="s4")
    # Build history with several entries to test specific_trace logic
    # Entries: index 0 model (decision False), index1 factor(decision True), index2 model(decision False), index3 factor(decision False)
    trace.hist.append((FakeExperiment("model"), FakeFeedback(decision=False)))
    trace.hist.append((FakeExperiment("factor"), FakeFeedback(decision=True)))
    trace.hist.append((FakeExperiment("model"), FakeFeedback(decision=False)))
    trace.hist.append((FakeExperiment("factor"), FakeFeedback(decision=False)))
    # Call prepare_context; action should be 'factor'
    ctx, ok = inst.prepare_context(trace)
    assert ok is True
    assert inst.targets == "factor"
    # Because action 'factor' and len(hist) == 4 (<6), RAG should be the easy suggestion
    assert "Try the easiest and fastest factors" in ctx["RAG"]
    # hypothesis_and_feedback should reflect the specific_trace built containing some elements:
    hyp_af = ctx["hypothesis_and_feedback"]
    assert hyp_af.startswith("HYP_AND_FEED_TRACE_LEN=")
    n = int(hyp_af.split("=")[1])
    # The specific_trace should include factor experiments (and the first SOTA model if present). Here we expect >0
    assert n > 0


def test_factor_rag_when_len_ge_6(monkeypatch):
    # Test the other RAG branch when action is factor and len(trace.hist) >= 6
    class Q:
        action_selection = "random"

    monkeypatch.setattr(quant_mod, "QUANT_PROP_SETTING", Q)
    # Force random.choice to choose 'factor'
    monkeypatch.setattr(quant_mod, "random", types.SimpleNamespace(choice=lambda lst: "factor"))
    inst = make_quant_instance()
    trace = FakeTrace(scen="s5")
    # Create 6 history entries to trigger the >=6 branch
    for i in range(6):
        trace.hist.append((FakeExperiment("factor" if i % 2 == 0 else "model"), FakeFeedback(decision=(i == 1))))
    ctx, ok = inst.prepare_context(trace)
    assert ok is True
    assert inst.targets == "factor"
    # Now RAG should be the "Now, you need to try factors that can achieve high IC" message
    assert "Now, you need to try factors that can achieve high IC" in ctx["RAG"]
