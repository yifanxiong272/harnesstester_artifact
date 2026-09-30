# file: rdagent/scenarios/data_science/proposal/exp_gen/proposal.py:318-489
# asked: {"lines": [324, 325, 335, 336, 337, 339, 340, 342, 343, 349, 350, 352, 353, 356, 358, 359, 360, 364, 365, 366, 367, 368, 369, 370, 371, 376, 377, 380, 381, 382, 386, 387, 388, 389, 390, 391, 392, 395, 396, 402, 404, 405, 406, 408, 411, 412, 413, 414, 415, 416, 417, 418, 419, 422, 423, 424, 425, 426, 429, 431, 432, 433, 435, 436, 437, 438, 439, 440, 441, 445, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 462, 463, 464, 465, 467, 468, 469, 470, 472, 473, 475, 477, 479, 481, 482, 483, 484, 486, 487, 489], "branches": [[324, 325], [324, 335], [336, 337], [336, 339], [395, 396], [395, 402], [404, 405], [404, 489], [405, 406], [405, 408], [481, 482], [481, 487]]}
# gained: {"lines": [324, 325, 335, 336, 339, 340, 342, 343, 349, 350, 352, 353, 356, 358, 359, 360, 364, 365, 366, 367, 368, 369, 370, 371, 376, 377, 380, 381, 382, 386, 387, 388, 389, 391, 392, 395, 396, 402, 404, 405, 406, 411, 412, 413, 414, 415, 416, 417, 418, 419, 422, 423, 424, 425, 426, 429, 435, 436, 437, 438, 439, 440, 441, 445, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 462, 463, 464, 465, 467, 468, 469, 470, 472, 473, 475, 477, 479, 481, 482, 483, 484, 486, 487, 489], "branches": [[324, 325], [324, 335], [336, 339], [395, 396], [395, 402], [404, 405], [404, 489], [405, 406], [481, 482]]}

import json
import pytest
from types import SimpleNamespace

import rdagent.scenarios.data_science.proposal.exp_gen.proposal as proposal_mod


class FakeTemplate:
    def __init__(self, key):
        self.key = key
        if "component_description" in key:
            self.template = {"compA": "DescA", "compB": "DescB"}
        else:
            self.template = {}

    def r(self, *args, **kwargs):
        return f"TPL[{self.key}]-args:{args}-kwargs:{kwargs}"


class FakeTFactory:
    def __call__(self, key):
        return FakeTemplate(key)


class FakeAPIBackend:
    def build_messages_and_create_chat_completion(self, *args, **kwargs):
        # Distinguish component generation (positional) vs direct generation (named user_prompt)
        if "user_prompt" in kwargs:
            resp = {
                "hypothesis_proposal": {
                    "hypothesis": "Test hypothesis",
                    "reason": "Hypothesis reason",
                    "concise_reason": "c_reason",
                    "concise_observation": "c_obs",
                    "concise_justification": "c_just",
                    "concise_knowledge": "c_know",
                },
                "task_design": {
                    "model_name": "model_v1",
                    "description": "Model description",
                },
                "workflow_update": "New workflow steps required",
            }
            return json.dumps(resp)
        else:
            resp = {"component": "Ensemble", "reason": "Component selected because..."}
            return json.dumps(resp)


class FakeTask:
    def __init__(self, name, description, **kwargs):
        self.name = name
        self.description = description
        self.extra = kwargs


class FakeDSExperiment:
    def __init__(self, pending_tasks_list=None, hypothesis=None, **kwargs):
        self.pending_tasks_list = pending_tasks_list or []
        self.hypothesis = hypothesis
        self.experiment_workspace = SimpleNamespace(
            file_dict={}, inject_code_from_file_dict=lambda other: setattr(self, "injected_from", other)
        )


def make_trace(sota_exp, last_exp):
    class FakeScen:
        def get_scenario_all_desc(self, eda_output=None):
            return f"SCEN_DESC eda={eda_output}"

    class Trace:
        def __init__(self, sota, last):
            self.scen = FakeScen()
            self._sota = sota
            self._last = last

        def sota_experiment(self):
            return self._sota

        def last_exp(self):
            return self._last

        def experiment_and_feedback_list_after_init(self, return_type="all"):
            return [("exp1", "fb1"), ("exp2", "fb2")]

    return Trace(sota_exp, last_exp)


def test_gen_returns_draft_if_present(monkeypatch):
    monkeypatch.setattr(proposal_mod, "draft_exp_in_decomposition", lambda scen, trace: "DRAFT_EXP")
    gen = proposal_mod.DSProposalV1ExpGen(SimpleNamespace())
    out = gen.gen(trace="ignored")
    assert out == "DRAFT_EXP"


def test_gen_main_flow_spec_enabled_and_workflow_added(monkeypatch):
    monkeypatch.setattr(proposal_mod, "draft_exp_in_decomposition", lambda scen, trace: None)
    monkeypatch.setattr(proposal_mod, "T", FakeTFactory())
    monkeypatch.setattr(proposal_mod, "APIBackend", FakeAPIBackend)

    def fake_get_component(component):
        if component in ("Model", "Ensemble"):
            return {
                "spec_file": "spec.txt",
                "target_name": "target_y",
                "task_output_format": {"fmt": "x"},
                "task_class": FakeTask,
                "extra_params": {"param_a": "default"},
            }
        return None

    monkeypatch.setattr(proposal_mod, "get_component", fake_get_component)
    monkeypatch.setattr(proposal_mod, "DS_RD_SETTING", SimpleNamespace(spec_enabled=True, enable_notebook_conversion=False))
    monkeypatch.setattr(proposal_mod, "DSExperiment", FakeDSExperiment)

    sota = FakeDSExperiment(pending_tasks_list=[[]])
    sota.experiment_workspace.file_dict = {"EDA.md": "EDA content", "spec.txt": "SPEC_CONTENT", "other.txt": "X"}
    last = FakeDSExperiment(pending_tasks_list=[[]])
    last.experiment_workspace.file_dict = {"some.py": "print('hi')"}

    trace = make_trace(sota, last)

    gen = proposal_mod.DSProposalV1ExpGen(SimpleNamespace())
    exp = gen.gen(trace=trace)

    assert isinstance(exp, FakeDSExperiment)
    assert len(exp.pending_tasks_list) >= 1
    first_task_list = exp.pending_tasks_list[0]
    assert isinstance(first_task_list, list)
    assert len(first_task_list) == 1
    task = first_task_list[0]
    assert isinstance(task, FakeTask)
    assert task.name == "model_v1"
    assert hasattr(exp, "injected_from")
    assert any(getattr(t, "name", "") == "Workflow" for sub in exp.pending_tasks_list for t in sub)


def test_gen_raises_value_error_for_unknown_component(monkeypatch):
    monkeypatch.setattr(proposal_mod, "draft_exp_in_decomposition", lambda scen, trace: None)
    monkeypatch.setattr(proposal_mod, "T", FakeTFactory())

    class APIBackendUnknown(FakeAPIBackend):
        def build_messages_and_create_chat_completion(self, *args, **kwargs):
            if "user_prompt" in kwargs:
                return super().build_messages_and_create_chat_completion(*args, **kwargs)
            else:
                return json.dumps({"component": "UnknownComponent", "reason": "Nope"})

    monkeypatch.setattr(proposal_mod, "APIBackend", APIBackendUnknown)
    monkeypatch.setattr(proposal_mod, "get_component", lambda c: None)
    monkeypatch.setattr(proposal_mod, "DS_RD_SETTING", SimpleNamespace(spec_enabled=False, enable_notebook_conversion=False))
    monkeypatch.setattr(proposal_mod, "DSExperiment", FakeDSExperiment)

    sota = FakeDSExperiment()
    sota.experiment_workspace.file_dict = {"EDA.md": "EDA"}
    last = FakeDSExperiment()
    last.experiment_workspace.file_dict = {}

    trace = make_trace(sota, last)

    gen = proposal_mod.DSProposalV1ExpGen(SimpleNamespace())

    with pytest.raises(ValueError):
        gen.gen(trace=trace)
