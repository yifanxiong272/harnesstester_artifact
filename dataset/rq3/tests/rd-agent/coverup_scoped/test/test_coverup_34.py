# file: rdagent/scenarios/data_science/proposal/exp_gen/draft/draft.py:183-239
# asked: {"lines": [192, 193, 195, 196, 197, 198, 199, 200, 202, 203, 204, 205, 206, 207, 209, 210, 211, 212, 213, 215, 216, 217, 219, 220, 221, 222, 223, 224, 226, 227, 228, 229, 231, 232, 233, 234, 235, 236, 238, 239], "branches": [[192, 193], [192, 195], [233, 234], [233, 239]]}
# gained: {"lines": [192, 193, 195, 196, 197, 198, 199, 200, 202, 203, 204, 205, 206, 207, 209, 210, 211, 212, 213, 215, 216, 217, 219, 220, 221, 222, 223, 224, 226, 227, 228, 229, 231, 232, 233, 234, 235, 236, 238, 239], "branches": [[192, 193], [192, 195], [233, 234], [233, 239]]}

import json
from types import SimpleNamespace

import pytest

import rdagent.scenarios.data_science.proposal.exp_gen.draft.draft as draft_mod


class DummyTask:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def __repr__(self):
        return f"DummyTask(name={self.name!r}, description={self.description!r})"


class DummyWorkflowTask:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def __repr__(self):
        return f"DummyWorkflowTask(name={self.name!r}, description={self.description!r})"


class DummyExp:
    def __init__(self, pending_tasks_list, hypothesis):
        # store by reference like original would
        self.pending_tasks_list = pending_tasks_list
        self.hypothesis = hypothesis

    def __repr__(self):
        return f"DummyExp(pending_tasks_list={self.pending_tasks_list!r}, hypothesis={self.hypothesis!r})"


class FakeAPIBackend:
    def __init__(self, response_json_str=None, supports_schema=False):
        # allow tests to set the json string to return
        self._response_json_str = response_json_str
        self._supports_schema = supports_schema

    def supports_response_schema(self):
        return self._supports_schema

    def build_messages_and_create_chat_completion(
        self, user_prompt=None, system_prompt=None, response_format=None, json_target_type=None
    ):
        # simply return the preconfigured JSON string
        if self._response_json_str is None:
            return json.dumps({})
        return self._response_json_str


class DummyTemplate:
    def r(self, **kwargs):
        # return a predictable string regardless of inputs; tests don't inspect it
        return "DUMMY_PROMPT"


def make_gen(monkeypatch, *, api_response_json: str, supports_schema: bool = False, component_info=None):
    """
    Helper to create a DSDraftV2ExpGen-like instance with necessary monkeypatches applied.
    Returns (gen, hypothesis) where gen is ready-to-call object and hypothesis is the object passed in.
    """

    # Patch APIBackend in the module to return our FakeAPIBackend configured per call
    def fake_api_backend_factory():
        return FakeAPIBackend(response_json_str=api_response_json, supports_schema=supports_schema)

    monkeypatch.setattr(draft_mod, "APIBackend", fake_api_backend_factory)

    # Patch T to avoid template resolution complexity
    monkeypatch.setattr(draft_mod, "T", lambda *_args, **_kwargs: DummyTemplate())

    # Patch DSExperiment and WorkflowTask and task_class provider get_component
    monkeypatch.setattr(draft_mod, "DSExperiment", DummyExp)
    monkeypatch.setattr(draft_mod, "WorkflowTask", DummyWorkflowTask)

    # default component_info if not provided
    if component_info is None:
        component_info = {
            "task_output_format": {"k": "v"},
            "target_name": "DefaultTarget",
            "task_class": DummyTask,
        }

    monkeypatch.setattr(draft_mod, "get_component", lambda key: component_info)

    # build the gen object without calling original __init__
    gen = object.__new__(draft_mod.DSDraftV2ExpGen)
    # minimal scen with processed_data_folder_description attribute
    gen.scen = SimpleNamespace(processed_data_folder_description="processed/data/folder")
    # set supports_response_schema according to passed flag (the real __init__ would call APIBackend().supports_response_schema())
    gen.supports_response_schema = supports_schema

    # create a simple hypothesis-like object with .component attribute
    hypothesis = SimpleNamespace(component=component_info.get("target_name", "DefaultTarget"))
    return gen, hypothesis


def test_task_gen_pipeline_true_description_string(monkeypatch):
    """
    Test the branch where pipeline == True. The component info should be fetched for "Pipeline",
    the API returns a JSON with task_design as a string, and workflow_update == "No update needed".
    Expect: one pending tasks list containing one task with description equal to that string.
    """
    # prepare API response where task_design is a string and no workflow update
    response = {"task_design": "This is a string description for the pipeline task", "workflow_update": "No update needed"}
    api_response_json = json.dumps(response)

    # Custom component info for "Pipeline"
    component_info_for_pipeline = {
        "task_output_format": {"fmt": "pipeline"},
        "target_name": "PipelineTarget",
        "task_class": DummyTask,
    }

    # create gen with monkeypatches
    gen, hypothesis = make_gen(
        monkeypatch,
        api_response_json=api_response_json,
        supports_schema=False,
        component_info=component_info_for_pipeline,
    )

    # ensure hypothesis.component is "Pipeline" so that get_component("Pipeline") branch is used
    hypothesis.component = "Pipeline"

    # Call task_gen with pipeline=True
    exp = gen.task_gen(
        component_desc="component desc",
        scenario_desc="scenario desc",
        hypothesis=hypothesis,
        pipeline=True,
        knowledge="some knowledge",
        failed_exp_feedback_list_desc="no failed exps",
    )

    # Verify returned experiment is our DummyExp and contains expected values
    assert isinstance(exp, DummyExp)
    # One pending tasks list (no workflow appended)
    assert isinstance(exp.pending_tasks_list, list)
    assert len(exp.pending_tasks_list) == 1
    first_group = exp.pending_tasks_list[0]
    assert isinstance(first_group, list)
    assert len(first_group) == 1
    task = first_group[0]
    # Task should be instance of DummyTask and have the name equal to hypothesis.component and description equal to string
    assert isinstance(task, DummyTask)
    assert task.name == hypothesis.component
    assert task.description == "This is a string description for the pipeline task"
    # Hypothesis should be preserved on experiment
    assert exp.hypothesis is hypothesis


def test_task_gen_non_pipeline_appends_workflow_and_description_fallback(monkeypatch):
    """
    Test the branch where pipeline == False and API returns a dict task_design without 'description',
    and workflow_update != "No update needed" so a WorkflowTask should be appended.
    Expect: first pending tasks list with a task whose description falls back to
    "{component_info['target_name']} description not provided", and second pending list containing WorkflowTask.
    """
    # task_design is a dict without 'description'
    response = {"task_design": {"some_key": "some_value"}, "workflow_update": "Please update the workflow to include step X"}
    api_response_json = json.dumps(response)

    # component info for the hypothesis.component (e.g., "ModelComp")
    component_info_for_model = {
        "task_output_format": {"fmt": "model"},
        "target_name": "ModelTargetName",
        "task_class": DummyTask,
    }

    gen, hypothesis = make_gen(
        monkeypatch,
        api_response_json=api_response_json,
        supports_schema=False,
        component_info=component_info_for_model,
    )

    # set hypothesis.component to something other than "Workflow" to satisfy workflow_check logic
    hypothesis.component = "Model"

    # Call task_gen with pipeline=False
    exp = gen.task_gen(
        component_desc="component desc",
        scenario_desc="scenario desc",
        hypothesis=hypothesis,
        pipeline=False,
        knowledge="some knowledge",
        failed_exp_feedback_list_desc="failures",
    )

    # Validate experiment structure
    assert isinstance(exp, DummyExp)
    # Should have two pending task groups: the generated task and the appended workflow task
    assert len(exp.pending_tasks_list) == 2

    # Validate first task description fallback occurred
    first_group = exp.pending_tasks_list[0]
    assert len(first_group) == 1
    task = first_group[0]
    assert isinstance(task, DummyTask)
    assert task.name == hypothesis.component
    # since task_design had no 'description', description should fall back to "<target_name> description not provided"
    expected_description = f"{component_info_for_model['target_name']} description not provided"
    assert task.description == expected_description

    # Validate workflow task appended
    second_group = exp.pending_tasks_list[1]
    assert len(second_group) == 1
    workflow_task = second_group[0]
    assert isinstance(workflow_task, DummyWorkflowTask)
    assert workflow_task.name == "Workflow"
    assert workflow_task.description == "Please update the workflow to include step X"
