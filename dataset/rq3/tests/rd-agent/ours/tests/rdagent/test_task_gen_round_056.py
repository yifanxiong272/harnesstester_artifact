import json
from types import SimpleNamespace
import pytest

import rdagent.scenarios.data_science.proposal.exp_gen.proposal as proposal

# The tests monkeypatch module-level symbols so they don't call external services.
# All test functions end with _round_056 as required.

class DummyPipelineTask:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.package_info = None


class DummyWorkflowTask:
    def __init__(self, name, description):
        self.name = name
        self.description = description


class DummyExperimentWorkspace:
    def __init__(self):
        self.injected = None

    def inject_code_from_file_dict(self, d):
        # record what was injected so tests can assert
        self.injected = d


class DummyDSExperiment:
    def __init__(self, pending_tasks_list=None, hypothesis=None, hypothesis_candidates=None):
        # mimic the real constructor signature used in task_gen
        self.pending_tasks_list = pending_tasks_list or []
        self.hypothesis = hypothesis
        self.hypothesis_candidates = hypothesis_candidates
        self.experiment_workspace = DummyExperimentWorkspace()
        self._user_instructions = None

    def set_user_instructions(self, ui):
        self._user_instructions = ui


def make_T_stub():
    # T(...) returns object with r(...) method that accepts any kwargs and returns a constant string
    class TObj:
        def r(self, **kwargs):
            # return something deterministic; the actual content isn't parsed by our stubs
            return "PROMPT"

    return lambda *args, **kwargs: TObj()


def make_APIBackend_stub(response_obj):
    class APIBackendStub:
        def build_messages_and_create_chat_completion(self, *, user_prompt, system_prompt, response_format, json_target_type):
            # ignore inputs and return deterministic JSON string
            return json.dumps(response_obj)

    return APIBackendStub


def test_task_gen_pipeline_schema_packages_and_sota_injection_round_056(monkeypatch):
    """
    Covers pipeline=True branch (line ~1200), supports_response_schema=True branch (line ~1237->1239),
    packages handling (~1261->1266) and sota_exp injection (~1269->1270).
    """
    # Patch component provider to return Pipeline-related info
    def get_component(name):
        return {
            "task_output_format": "fmt",
            "target_name": "PipelineTarget",
            "task_class": DummyPipelineTask,
        }

    monkeypatch.setattr(proposal, "get_component", get_component)

    # Patch template helper and settings
    monkeypatch.setattr(proposal, "T", make_T_stub())
    monkeypatch.setattr(proposal, "DS_RD_SETTING", SimpleNamespace(fix_seed_and_data_split=True))

    # Patch APIBackend to return a dict with 'sketch' and 'packages'
    response_obj = {"sketch": "main task sketch description", "packages": ["pkgA", "pkgB"]}
    monkeypatch.setattr(proposal, "APIBackend", make_APIBackend_stub(response_obj))

    # Patch classes used by the function
    monkeypatch.setattr(proposal, "PipelineTask", DummyPipelineTask)
    monkeypatch.setattr(proposal, "WorkflowTask", DummyWorkflowTask)
    monkeypatch.setattr(proposal, "DSExperiment", DummyDSExperiment)

    # Patch get_packages to return a deterministic value
    monkeypatch.setattr(proposal, "get_packages", lambda pkgs: {"installed": list(pkgs)})

    # Build a minimal 'self' with required attributes
    self_obj = SimpleNamespace()
    self_obj.supports_response_schema = True
    self_obj.scen = SimpleNamespace(processed_data_folder_description="/data/folder", metric_name="accuracy")

    # Build hypotheses and candidates
    hypothesis = SimpleNamespace(component="Pipeline")
    hypotheses = [hypothesis]
    hypotheses_candidates = []

    # Create a fake sota_exp that has an experiment_workspace (we'll pass a dict and expect it to be injected)
    sota_exp = SimpleNamespace(experiment_workspace={"some": "code"})

    # Call the unbound function (method) with our fake self
    exp = proposal.DSProposalV2ExpGen.task_gen(
        self_obj,
        component_desc="comp_desc",
        scenario_desc="scenario",
        sota_exp_desc="sota desc",
        sota_exp=sota_exp,
        hypotheses=hypotheses,
        hypotheses_candidates=hypotheses_candidates,
        pipeline=True,
        failed_exp_feedback_list_desc="",
        fb_to_sota_exp=None,
        sibling_exp=None,
        former_user_instructions=None,
    )

    # Assertions (observable behavior):
    # - The result is our DummyDSExperiment instance
    assert isinstance(exp, DummyDSExperiment)
    # - The main task was created and placed in pending_tasks_list
    assert exp.pending_tasks_list and isinstance(exp.pending_tasks_list[0][0], DummyPipelineTask)
    assert exp.pending_tasks_list[0][0].description == "main task sketch description"
    # - packages branch executed and package_info was set to get_packages result
    assert exp.pending_tasks_list[0][0].package_info == {"installed": ["pkgA", "pkgB"]}
    # - sota_exp injection happened: the new experiment's workspace.injected matches what was passed
    assert exp.experiment_workspace.injected == sota_exp.experiment_workspace


def test_task_gen_non_pipeline_workflow_update_and_set_user_instructions_round_056(monkeypatch):
    """
    Covers pipeline=False branch where hypothesis.component != 'Workflow' so workflow_check=True (~1203, ~1241->1243),
    also covers workflow_task creation (~1273->1274) and former_user_instructions setting (~1281->1283).
    Also covers sibling_exp handling (line ~1207) and nested task_design description path (line ~1241->1243).
    """
    # get_component returns generic component info with DummyPipelineTask as task_class
    def get_component(name):
        return {"task_output_format": None, "target_name": "CompTarget", "task_class": DummyPipelineTask}

    monkeypatch.setattr(proposal, "get_component", get_component)
    monkeypatch.setattr(proposal, "T", make_T_stub())
    monkeypatch.setattr(proposal, "DS_RD_SETTING", SimpleNamespace(fix_seed_and_data_split=False))

    # Response includes task_design and workflow_update keys
    response_obj = {"task_design": {"description": "designed task description"}, "workflow_update": "do X"}
    monkeypatch.setattr(proposal, "APIBackend", make_APIBackend_stub(response_obj))

    monkeypatch.setattr(proposal, "PipelineTask", DummyPipelineTask)
    monkeypatch.setattr(proposal, "WorkflowTask", DummyWorkflowTask)
    monkeypatch.setattr(proposal, "DSExperiment", DummyDSExperiment)

    # No packages key -> get_packages should not be invoked, but ensure it exists if called
    monkeypatch.setattr(proposal, "get_packages", lambda pkgs: {"installed": list(pkgs)})

    # Build self
    self_obj = SimpleNamespace()
    self_obj.supports_response_schema = False
    self_obj.scen = SimpleNamespace(processed_data_folder_description="dataX", metric_name="f1")

    # hypothesis not 'Workflow' -> workflow_check True
    hypothesis = SimpleNamespace(component="Model")
    hypotheses = [hypothesis]
    hypotheses_candidates = []

    # sibling_exp: create an object with pending_tasks_list nested structure
    other_task = SimpleNamespace(description="sibling_task_description")
    sibling_exp = [SimpleNamespace(pending_tasks_list=[[other_task]])]

    # former_user_instructions stub (any object is ok; ensure set_user_instructions records it)
    former_ui = "please follow previous instructions"

    exp = proposal.DSProposalV2ExpGen.task_gen(
        self_obj,
        component_desc="comp",
        scenario_desc="scenarioX",
        sota_exp_desc="sota",
        sota_exp=None,
        hypotheses=hypotheses,
        hypotheses_candidates=hypotheses_candidates,
        pipeline=False,
        failed_exp_feedback_list_desc="",  # not used in our stubbed flow
        fb_to_sota_exp=None,
        sibling_exp=sibling_exp,
        former_user_instructions=former_ui,
    )

    # Assertions:
    assert isinstance(exp, DummyDSExperiment)
    # main task description should come from task_design.description
    assert exp.pending_tasks_list[0][0].description == "designed task description"
    # a workflow task should have been appended as the second pending_tasks_list entry
    assert len(exp.pending_tasks_list) >= 2
    assert isinstance(exp.pending_tasks_list[1][0], DummyWorkflowTask)
    assert exp.pending_tasks_list[1][0].description == "do X"
    # former_user_instructions should have been set on experiment
    assert exp._user_instructions == former_ui


def test_task_gen_non_pipeline_component_workflow_description_branch_round_056(monkeypatch):
    """
    Covers the branch where pipeline=False and hypothesis.component == 'Workflow', so workflow_check=False,
    and the code should take task_desc from task_dict.get('description', ...).
    """
    def get_component(name):
        return {"task_output_format": None, "target_name": "WT", "task_class": DummyPipelineTask}

    monkeypatch.setattr(proposal, "get_component", get_component)
    monkeypatch.setattr(proposal, "T", make_T_stub())
    monkeypatch.setattr(proposal, "DS_RD_SETTING", SimpleNamespace(fix_seed_and_data_split=False))

    # Response contains direct 'description' key
    response_obj = {"description": "direct description"}
    monkeypatch.setattr(proposal, "APIBackend", make_APIBackend_stub(response_obj))

    monkeypatch.setattr(proposal, "PipelineTask", DummyPipelineTask)
    monkeypatch.setattr(proposal, "WorkflowTask", DummyWorkflowTask)
    monkeypatch.setattr(proposal, "DSExperiment", DummyDSExperiment)
    monkeypatch.setattr(proposal, "get_packages", lambda pkgs: {"installed": list(pkgs)})

    self_obj = SimpleNamespace()
    self_obj.supports_response_schema = False
    self_obj.scen = SimpleNamespace(processed_data_folder_description="d", metric_name="m")

    hypothesis = SimpleNamespace(component="Workflow")
    hypotheses = [hypothesis]
    hypotheses_candidates = []

    exp = proposal.DSProposalV2ExpGen.task_gen(
        self_obj,
        component_desc="c",
        scenario_desc="s",
        sota_exp_desc="st",
        sota_exp=None,
        hypotheses=hypotheses,
        hypotheses_candidates=hypotheses_candidates,
        pipeline=False,
        failed_exp_feedback_list_desc="",
        fb_to_sota_exp=None,
        sibling_exp=None,
        former_user_instructions=None,
    )

    assert isinstance(exp, DummyDSExperiment)
    assert exp.pending_tasks_list[0][0].description == "direct description"
