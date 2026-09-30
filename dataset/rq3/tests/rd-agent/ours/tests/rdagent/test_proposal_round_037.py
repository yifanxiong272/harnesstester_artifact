import json
import types
from types import SimpleNamespace
import pytest

from rdagent.scenarios.data_science.proposal.exp_gen import proposal as mod

# Helpers / fakes used to patch the module under test deterministically
class FakeWorkspace:
    def __init__(self, file_dict=None):
        self.file_dict = file_dict or {}
        self.injected_from = None

    def inject_code_from_file_dict(self, other):
        # record that injection was attempted and with what
        self.injected_from = getattr(other, "file_dict", other)


class FakeDSExperiment:
    def __init__(self, *args, pending_tasks_list=None, hypothesis=None, experiment_workspace=None, **kwargs):
        # When used as a SOTA experiment, test will pass experiment_workspace
        if experiment_workspace is not None:
            self.experiment_workspace = experiment_workspace
        else:
            # When created by gen(...) to be returned, provide a workspace with injector
            self.experiment_workspace = FakeWorkspace()
        self.pending_tasks_list = pending_tasks_list
        self.hypothesis = hypothesis


class FakeDSHypothesis:
    def __init__(self, **kwargs):
        self.kw = kwargs


class FakeTask:
    def __init__(self, name, description, **kwargs):
        self.name = name
        self.description = description
        self.extra = kwargs


class FakeWorkflowTask:
    def __init__(self, name, description):
        self.name = name
        self.description = description


class FakeTemplate:
    def __init__(self, key):
        # create a template mapping so code path that iterates .template.items() works
        self.template = {"k": "v"}
        self.key = key

    def r(self, **kwargs):
        # return a string representative of rendering
        return f"rendered({self.key})"


class FakeAPIBackend:
    def __init__(self):
        pass

    def build_messages_and_create_chat_completion(self, *args, **kwargs):
        # Distinguish the first call (component generation) vs the second (detailed generation)
        # First call uses positional args (component_user_prompt, component_sys_prompt)
        # Second call uses kwargs user_prompt=...
        if "user_prompt" in kwargs:
            # This is the second call inside _f: return hypothesis_proposal and task_design
            resp = {
                "hypothesis_proposal": {
                    "hypothesis": "h1",
                    "reason": "hr",
                    "concise_reason": "cr",
                    "concise_observation": "co",
                    "concise_justification": "cj",
                    "concise_knowledge": "ck",
                },
                "task_design": {
                    # When component == 'Model' code will select model_name
                    "model_name": "Model",
                    "description": "task desc",
                },
                # Provide a non-default workflow update string to exercise the branch that appends a WorkflowTask
                "workflow_update": "Please update workflow to include step X",
            }
            return json.dumps(resp)
        else:
            # First call: component generation. Return Ensemble to exercise the conversion to Model when file count <= 1
            return json.dumps({"component": "Ensemble", "reason": "component chosen because"})


class FakeTFactory:
    def __init__(self):
        pass

    def __call__(self, key):
        return FakeTemplate(key)


# Test 1: draft_exp_in_decomposition early return
def test_draft_in_decomposition_returns_early_round_037(monkeypatch):
    # Patch draft_exp_in_decomposition to return a sentinel value
    monkeypatch.setattr(mod, "draft_exp_in_decomposition", lambda scen, trace: "DRAFT-EXP")

    # Create a minimal trace (not used because draft hits first)
    fake_trace = SimpleNamespace()

    # Provide minimal scen required by ExpGen.__init__
    fake_scen = SimpleNamespace()

    gen = mod.DSProposalV1ExpGen(fake_scen)
    res = gen.gen(fake_trace)

    assert res == "DRAFT-EXP"


# Test 2: full path where component is initially 'Ensemble', converted to 'Model', spec_enabled True,
# workflow_update returned => appends a WorkflowTask
def test_gen_full_flow_appends_workflow_and_injects_code_round_037(monkeypatch):
    # Patch symbols in module
    monkeypatch.setattr(mod, "DSExperiment", FakeDSExperiment)
    monkeypatch.setattr(mod, "DSHypothesis", FakeDSHypothesis)
    monkeypatch.setattr(mod, "APIBackend", FakeAPIBackend)
    monkeypatch.setattr(mod, "T", FakeTFactory())
    monkeypatch.setattr(mod, "WorkflowTask", FakeWorkflowTask)

    # Provide DS_RD_SETTING with spec_enabled True so code tries to read spec_file from sota_exp workspace
    monkeypatch.setattr(mod, "DS_RD_SETTING", SimpleNamespace(spec_enabled=True, enable_notebook_conversion=False))

    # Patch generate_diff_from_dict to deterministic value
    monkeypatch.setattr(mod, "generate_diff_from_dict", lambda a, b: ["diffline"])

    # Patch get_component to return info for Model (it will be called with component after conversion)
    component_info = {
        "spec_file": "component_spec.md",
        "target_name": "target_col",
        "task_class": FakeTask,
        "task_output_format": "fmt",
        "extra_params": {},
    }
    monkeypatch.setattr(mod, "get_component", lambda comp: component_info if comp == "Model" else None)

    # Patch draft_exp_in_decomposition to return falsy so full flow continues
    monkeypatch.setattr(mod, "draft_exp_in_decomposition", lambda scen, trace: None)

    # Prepare a sota experiment with a workspace file_dict containing only one model file -> file count == 1
    sota_workspace = FakeWorkspace(file_dict={"model_v1.py": "print(1)"})
    sota_exp = FakeDSExperiment(experiment_workspace=sota_workspace)

    # Prepare last_exp with empty files (so generate_diff_from_dict returns diffline as patched)
    last_workspace = FakeWorkspace(file_dict={})
    last_exp = FakeDSExperiment(experiment_workspace=last_workspace)

    # Trace object implementing required methods used by gen
    class FakeTrace:
        def __init__(self, sota, last):
            self._sota = sota
            self._last = last
            self.scen = SimpleNamespace(get_scenario_all_desc=lambda eda_output=None: "SCEN-DESC")

        def sota_experiment(self):
            return self._sota

        def last_exp(self):
            return self._last

        def experiment_and_feedback_list_after_init(self, return_type="all"):
            return ["fb1", "fb2"]

    trace = FakeTrace(sota_exp, last_exp)

    # Provide minimal scen required by ExpGen.__init__
    fake_scen = SimpleNamespace()

    # Instantiate generator and run
    gen = mod.DSProposalV1ExpGen(fake_scen)
    exp = gen.gen(trace)

    # Assertions about returned experiment
    assert isinstance(exp, FakeDSExperiment)
    # It should have been constructed with pending_tasks_list and hypothesis
    assert exp.pending_tasks_list is not None
    # First pending task should be our FakeTask inside a nested list
    assert isinstance(exp.pending_tasks_list[0][0], FakeTask)
    assert exp.pending_tasks_list[0][0].name == "Model"
    assert exp.pending_tasks_list[0][0].description == "task desc"

    # Because the mocked API returned a workflow_update string, a WorkflowTask should be appended
    # The code appends a list containing a WorkflowTask
    assert len(exp.pending_tasks_list) >= 2
    appended = exp.pending_tasks_list[-1][0]
    assert isinstance(appended, FakeWorkflowTask)
    assert appended.name == "Workflow"
    assert "update workflow" in appended.description.lower() or "please update" in appended.description.lower()

    # Confirm that inject_code_from_file_dict was called with the sota workspace
    assert exp.experiment_workspace.injected_from == sota_workspace.file_dict


if __name__ == "__main__":
    pytest.main([__file__])
