import sys
import types
import builtins
import importlib
import pytest

import rdagent.log.ui.storage as storage

# Helper to inject fake modules into import system
def make_module(**attrs):
    m = types.ModuleType("fake")
    for k, v in attrs.items():
        setattr(m, k, v)
    return m

@pytest.fixture(autouse=True)
def patch_loopid_and_evoid(monkeypatch):
    # deterministic loop id and evo id for all tests
    monkeypatch.setattr(storage, "extract_loopid_func_name", lambda tag: ("LOOP123", "fn"))
    monkeypatch.setattr(storage, "extract_evoid", lambda tag: "42")
    yield

def install_module(monkeypatch, name, module):
    # ensure module is available for dynamic 'from X import Y' inside the function under test
    monkeypatch.setitem(sys.modules, name, module)

# 1) Hypothesis generation branch
def test_hypothesis_generation_round_017(monkeypatch):
    # create fake Hypothesis class and module
    class Hypothesis:
        def __init__(self):
            self.hypothesis = "htext"
            self.reason = "r"
            self.concise_reason = "cr"
            self.concise_justification = "cj"
            self.concise_observation = "co"
            self.concise_knowledge = "ck"

    mod = make_module(Hypothesis=Hypothesis)
    install_module(monkeypatch, "rdagent.core.proposal", mod)

    ws = storage.WebStorage(0, "")
    h = Hypothesis()
    out = ws._obj_to_json(h, "hypothesis generation: run", "ID-1", "TS-1")

    assert isinstance(out, dict)
    assert out["id"] == "ID-1"
    assert out["msg"]["tag"] == "research.hypothesis"
    content = out["msg"]["content"]
    assert content["hypothesis"] == "htext"
    assert content["reason"] == "r"
    assert content["concise_reason"] == "cr"

# 2) PDF image branch
def test_pdf_image_branch_round_017(monkeypatch):
    ws = storage.WebStorage(0, "")
    out = ws._obj_to_json(object(), "some pdf_image capture", "ID-IMG", "2026-01-01T00:00:00Z")

    assert isinstance(out, dict)
    assert out["id"] == "ID-IMG"
    assert out["msg"]["tag"] == "research.pdf_image"
    assert out["msg"]["content"]["image"] == "2026-01-01T00:00:00Z.jpg"

# 3) Experiment generation with FactorTask
def test_experiment_generation_factor_round_017(monkeypatch):
    class FactorTask:
        def __init__(self, name):
            self.factor_name = name
            self.factor_description = name + "-desc"
            self.factor_formulation = name + "-form"
            self.variables = {"x": 1}

    # model task class provided as well to satisfy import
    class ModelTask:
        pass

    install_module(monkeypatch, "rdagent.components.coder.factor_coder.factor", make_module(FactorTask=FactorTask))
    install_module(monkeypatch, "rdagent.components.coder.model_coder.model", make_module(ModelTask=ModelTask))

    ws = storage.WebStorage(0, "")
    tasks = [FactorTask("F1"), FactorTask("F2")]
    out = ws._obj_to_json(tasks, "experiment generation: create", "EID-F", "TSF")

    assert out["msg"]["tag"] == "research.tasks"
    content = out["msg"]["content"]
    assert isinstance(content, list)
    assert content[0]["name"] == "F1"
    assert content[1]["description"] == "F2-desc"

# 4) Experiment generation with ModelTask
def test_experiment_generation_model_round_017(monkeypatch):
    class FactorTask:
        pass

    class ModelTask:
        def __init__(self, name):
            self.name = name
            self.description = name + "-d"
            self.model_type = "mt"
            self.formulation = "form"
            self.variables = {"a": 2}

    install_module(monkeypatch, "rdagent.components.coder.factor_coder.factor", make_module(FactorTask=FactorTask))
    install_module(monkeypatch, "rdagent.components.coder.model_coder.model", make_module(ModelTask=ModelTask))

    ws = storage.WebStorage(0, "")
    tasks = [ModelTask("M1")]
    out = ws._obj_to_json(tasks, "experiment generation: model", "EID-M", "TSM")

    assert out["msg"]["tag"] == "research.tasks"
    content = out["msg"]["content"]
    assert content[0]["model_type"] == "mt"
    assert content[0]["name"] == "M1"

# 5) direct_exp_gen producing hypothesis + tasks with architecture path
def test_direct_exp_gen_round_017(monkeypatch):
    # DSHypothesis
    class DSHypothesis:
        def __init__(self):
            self.hypothesis = "H"
            self.reason = "R"
            self.component = "COMP"
            self.concise_reason = "cr"
            self.concise_justification = "cj"
            self.concise_observation = "co"
            self.concise_knowledge = "ck"

    class DSExperiment:
        def __init__(self):
            self.hypothesis = DSHypothesis()
            # pending_tasks_list is list of tuples (task, ...)
            t = types.SimpleNamespace()
            t.name = "TaskName"
            t.description = "TaskDesc"
            t.model_type = "MT"
            t.architecture = "Arch"
            t.hyperparameters = {"lr": 0.1}
            self.pending_tasks_list = [(t,)]

    install_module(monkeypatch, "rdagent.scenarios.data_science.experiment.experiment", make_module(DSExperiment=DSExperiment))
    install_module(monkeypatch, "rdagent.scenarios.data_science.proposal.exp_gen.base", make_module(DSHypothesis=DSHypothesis))

    ws = storage.WebStorage(0, "")
    exp = DSExperiment()
    out = ws._obj_to_json(exp, "direct_exp_gen: new", "DX", "TSD")

    assert isinstance(out, list)
    assert out[0]["msg"]["tag"] == "research.hypothesis"
    assert out[1]["msg"]["tag"] == "research.tasks"
    tasks_content = out[1]["msg"]["content"]
    assert tasks_content[0][0]["name"] == "TaskName"
    # when architecture exists, architecture key should be present in the inner dict
    assert "architecture" in tasks_content[0][0]

# 6) evolving code branch
def test_evolving_code_round_017(monkeypatch):
    class FBWorkspace:
        def __init__(self, name, target_task=None):
            self.file_dict = {"file": name}
            self.target_task = target_task

    target = types.SimpleNamespace(name="TargetTask")
    ws_objs = [FBWorkspace("f1", target), FBWorkspace("f2", None)]

    install_module(monkeypatch, "rdagent.core.experiment", make_module(FBWorkspace=FBWorkspace))

    ws = storage.WebStorage(0, "")
    tag = "evo_loop_42.evolving code"
    out = ws._obj_to_json(ws_objs, tag, "EVOID", "TS")

    assert out["msg"]["tag"] == "evolving.codes"
    content = out["msg"]["content"]
    assert content[0]["evo_id"] == "42"
    assert content[0]["workspace"] == {"file": "f1"}
    assert content[1]["target_task_name"] == "PipelineTask"

# 7) evolving feedback branch
def test_evolving_feedback_round_017(monkeypatch):
    class CoSTEERSingleFeedback:
        def __init__(self):
            self.final_decision = "OK"
            self.execution = "exec"
            self.code = "code"
            self.return_checking = True

    install_module(monkeypatch, "rdagent.components.coder.CoSTEER.evaluators", make_module(CoSTEERSingleFeedback=CoSTEERSingleFeedback))

    ws_objs = [CoSTEERSingleFeedback()]
    ws = storage.WebStorage(0, "")
    tag = "evo_loop_42.evolving feedback"
    out = ws._obj_to_json(ws_objs, tag, "EVOFB", "TST")

    assert out["msg"]["tag"] == "evolving.feedbacks"
    cont = out["msg"]["content"]
    assert cont[0]["final_decision"] == "OK"
    assert cont[0]["execution"] == "exec"

# 8) scenario branch
def test_scenario_branch_round_017(monkeypatch):
    obj = types.SimpleNamespace(experiment_setting={"k": "v"})
    ws = storage.WebStorage(0, "")
    out = ws._obj_to_json(obj, "my scenario config", "SID", "TS")

    assert out["msg"]["tag"] == "feedback.config"
    assert out["msg"]["content"]["config"] == {"k": "v"}

# 9) Quantitative Backtesting Chart branch
def test_qbacktesting_chart_round_017(monkeypatch):
    # provide fake plotly.io.to_html and qlib report_figure
    plotly_mod = types.ModuleType("plotly")
    io_mod = types.ModuleType("io")
    io_mod.to_html = lambda fig: "<html>FIG</html>"
    plotly_mod.io = io_mod
    install_module(monkeypatch, "plotly", plotly_mod)

    def report_figure(x):
        return "figure-repr"

    install_module(monkeypatch, "rdagent.log.ui.qlib_report_figure", make_module(report_figure=report_figure))

    ws = storage.WebStorage(0, "")
    dummy = object()
    out = ws._obj_to_json(dummy, "Quantitative Backtesting Chart", "QB", "TSQ")

    assert out["msg"]["tag"] == "feedback.return_chart"
    assert out["msg"]["content"]["chart_html"] == "<html>FIG</html>"

# 10) running branch: normal and AttributeError fallback
def test_running_branch_normal_round_017(monkeypatch):
    class ResultObj:
        def to_json(self):
            return "{\"ok\": true}"

    class Experiment:
        def __init__(self):
            self.result = ResultObj()

    install_module(monkeypatch, "rdagent.core.experiment", make_module(Experiment=Experiment))

    exp = Experiment()
    ws = storage.WebStorage(0, "")
    out = ws._obj_to_json(exp, "running now", "RID", "TSR")

    assert out["msg"]["tag"] == "feedback.metric"
    assert out["msg"]["content"]["result"] == '{"ok": true}'

def test_running_branch_attr_error_fallback_round_017(monkeypatch):
    class ResultObj:
        def to_json(self):
            return "{\"val\": 2}"

    class Experiment:
        @property
        def result(self):
            raise AttributeError("no direct property")

    e = Experiment()
    # set raw dict value to simulate compatibility fallback
    e.__dict__["result"] = ResultObj()

    install_module(monkeypatch, "rdagent.core.experiment", make_module(Experiment=Experiment))

    ws = storage.WebStorage(0, "")
    out = ws._obj_to_json(e, "running case", "RID2", "TSR2")

    assert out["msg"]["tag"] == "feedback.metric"
    assert out["msg"]["content"]["result"] == '{"val": 2}'

# 11) feedback branch: HypothesisFeedback vs ExperimentFeedback
def test_feedback_branch_hypothesis_round_017(monkeypatch):
    class HypothesisFeedback:
        def __init__(self):
            self.observations = [1, 2]
            self.hypothesis_evaluation = "heval"
            self.new_hypothesis = None
            self.decision = "d"
            self.reason = "r"
            self.exception = None

    class ExperimentFeedback:
        def __init__(self):
            self.decision = "DX"
            self.reason = "RX"
            self.exception = None

    install_module(monkeypatch, "rdagent.core.proposal", make_module(ExperimentFeedback=ExperimentFeedback, HypothesisFeedback=HypothesisFeedback))

    hfb = HypothesisFeedback()
    ws = storage.WebStorage(0, "")
    out = ws._obj_to_json(hfb, "feedback here", "FBID", "TSFB")

    assert out["msg"]["tag"] == "feedback.hypothesis_feedback"
    assert "observations" in out["msg"]["content"]

    ef = ExperimentFeedback()
    out2 = ws._obj_to_json(ef, "feedback here", "FBID2", "TSFB2")
    assert out2["msg"]["content"]["decision"] == "DX"
