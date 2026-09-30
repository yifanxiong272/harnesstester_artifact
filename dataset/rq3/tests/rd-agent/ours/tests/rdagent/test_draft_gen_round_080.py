import importlib
import types
from types import SimpleNamespace


# Tests for DSDraftExpGen.gen to cover branches around last_successful_exp, search_list, and DS_RD_SETTING

def _make_fake_task(get_info=None):
    class FakeTask:
        def __init__(self, name=None, description=None):
            self.name = name
            self.description = description

        def get_task_information(self):
            # used when constructing former_tasks_desc for earlier experiments
            return get_info() if get_info else f"info_for_{self.name}"

    return FakeTask


class _FakeWorkspace:
    def __init__(self, file_dict=None, workspace_path=None):
        self.file_dict = file_dict or {}
        self.workspace_path = workspace_path or "/tmp"
        self.injected_from = None

    def inject_code_from_file_dict(self, other_workspace):
        # record that injection occurred and what was injected
        # other_workspace may be a workspace object or just a dict
        if hasattr(other_workspace, 'file_dict'):
            self.injected_from = other_workspace.file_dict
        else:
            self.injected_from = other_workspace


class _FakeDSExperiment:
    def __init__(self, pending_tasks_list=None, hypothesis=None, workspace=None):
        # replicate minimal constructor used by gen()
        self.pending_tasks_list = pending_tasks_list or []
        self.hypothesis = hypothesis
        # ensure experiment_workspace exists as attribute used by gen()
        self.experiment_workspace = workspace or _FakeWorkspace()


class _FakeFB:
    def __init__(self, exception):
        self.exception = exception


class _FakeScen:
    def __init__(self):
        self.last_eda = None

    def get_scenario_all_desc(self, eda_output=None):
        # echo the eda_output so tests can assert it was passed through
        self.last_eda = eda_output
        return f"scenario_desc_with_eda:{eda_output}"


class _FakeTrace:
    def __init__(self, last_successful_exp=None, search_list=None):
        self._last = last_successful_exp
        self._search = search_list or []
        self.scen = _FakeScen()

    def last_successful_exp(self):
        return self._last

    def retrieve_search_list(self):
        return list(self._search)


class _FakeT:
    def __init__(self, key):
        self.key = key

    def r(self, **kwargs):
        # deterministic resolution: return different sentinel depending on key
        if 'component_spec' in self.key:
            # mimic returning a spec string when asked
            return f"resolved_spec_for_{self.key}"
        return f"resolved_output_format_for_{self.key}"


def _patch_module(module):
    # Patch the module to ensure deterministic, isolated behavior
    # Provide simple classes and settings used by gen()
    FakeTask = _make_fake_task()

    module.DataLoaderTask = FakeTask
    module.FeatureTask = FakeTask
    module.ModelTask = FakeTask
    module.EnsembleTask = FakeTask
    module.WorkflowTask = FakeTask

    # Patch DSExperiment used for isinstance checks and construction
    module.DSExperiment = _FakeDSExperiment

    # Provide a simple DS_RD_SETTING namespace that tests can toggle
    module.DS_RD_SETTING = SimpleNamespace(spec_enabled=False, enable_notebook_conversion=False)

    # Patch T used to resolve prompts/specs
    module.T = lambda key: _FakeT(key)


def test_gen_no_last_success_round_080():
    """Case: last_successful_exp is falsy -> eda_output None branch; no search_list entries; spec resolved via T when spec_enabled False."""
    module = importlib.import_module('rdagent.scenarios.data_science.proposal.exp_gen.draft.draft')
    _patch_module(module)

    # Build a trace that has no last successful experiment and no search history
    trace = _FakeTrace(last_successful_exp=None, search_list=[])

    # Create DSDraftExpGen instance without calling __init__ to avoid side effects
    gen_instance = module.DSDraftExpGen.__new__(module.DSDraftExpGen)

    # Replace the _init_task_gen to capture arguments and return empty dict -> triggers default description
    captured = {}

    def fake_init_task_gen(*, targets, scenario_desc, spec, task_output_format, former_task=None, **kwargs):
        captured['targets'] = targets
        captured['scenario_desc'] = scenario_desc
        captured['spec'] = spec
        captured['task_output_format'] = task_output_format
        captured['former_task'] = former_task
        return {}

    gen_instance._init_task_gen = fake_init_task_gen

    # Call gen for DataLoadSpec
    result_exp = gen_instance.gen('DataLoadSpec', trace, plan=None)

    # Assertions: default description used, name equals component, no injection from last_successful_exp
    task = result_exp.pending_tasks_list[0][0]
    assert task.name == 'DataLoadSpec', "Task name should be the component name when not Model"
    assert task.description == 'DataLoadSpec description not provided'

    # T.r() should have been used to resolve task_output_format and spec (since spec_enabled False)
    assert captured['task_output_format'].startswith('resolved_output_format_for_'), "task_output_format should be resolved by patched T"
    assert isinstance(captured['spec'], str) and captured['spec'].startswith('resolved_spec_for_'), "spec should be resolved via patched T when spec_enabled is False"


def test_gen_with_last_success_and_search_round_080():
    """Case: last_successful_exp is DSExperiment -> eda_output from file_dict; search_list non-empty -> former_tasks_desc built; spec pulled from last_successful_exp when spec_enabled True; Model component uses model_name from resp_dict."""
    module = importlib.import_module('rdagent.scenarios.data_science.proposal.exp_gen.draft.draft')
    _patch_module(module)

    # Prepare a last successful experiment that is an instance of the patched DSExperiment
    last_ws = _FakeWorkspace(file_dict={'EDA.md': 'eda_content', 'spec/model.md': 'model_spec_value'})
    last_exp = module.DSExperiment(pending_tasks_list=[], hypothesis=None, workspace=last_ws)

    # Prepare a previous failed experiment in search_list with a task that exposes get_task_information
    PrevTask = _make_fake_task(lambda: 'prev_task_information')
    prev_exp = module.DSExperiment(pending_tasks_list=[[PrevTask('p', 'd')]], hypothesis=None, workspace=_FakeWorkspace(file_dict={}))
    fb = _FakeFB(exception='boom')

    trace = _FakeTrace(last_successful_exp=last_exp, search_list=[(prev_exp, fb)])

    # Ensure spec_enabled True to follow the branch that reads spec from last_successful_exp
    module.DS_RD_SETTING.spec_enabled = True

    # Create generator instance without running __init__
    gen_instance = module.DSDraftExpGen.__new__(module.DSDraftExpGen)

    # Capture the former_task passed into _init_task_gen and return a dict with model_name
    captured = {}

    def fake_init_task_gen(*, targets, scenario_desc, spec, task_output_format, former_task=None, **kwargs):
        captured['targets'] = targets
        captured['scenario_desc'] = scenario_desc
        captured['spec'] = spec
        captured['task_output_format'] = task_output_format
        captured['former_task'] = former_task
        # return model_name to test the Model name-pop behavior
        return {'model_name': 'super_model', 'description': 'model description provided'}

    gen_instance._init_task_gen = fake_init_task_gen

    # Call gen for Model component
    result_exp = gen_instance.gen('Model', trace, plan=None)

    # The EDA output should have been passed into scen.get_scenario_all_desc
    assert trace.scen.last_eda == 'eda_content', "EDA.md content from last_successful_exp should be passed into scen.get_scenario_all_desc"

    # The spec should be read from last_successful_exp.file_dict when spec_enabled is True
    assert captured['spec'] == 'model_spec_value', "Spec should be taken from last_successful_exp.experiment_workspace.file_dict for the Model component when spec_enabled is True"

    # former_task should include the previous failure exception message
    assert 'boom' in captured['former_task'], "former_task description should include the exception text from feedback"

    # For Model, name should be popped from resp_dict (model_name)
    task = result_exp.pending_tasks_list[0][0]
    assert task.name == 'super_model', "Model task name should use the returned model_name from _init_task_gen"
    assert task.description == 'model description provided'

    # Because last_successful_exp is truthy, injection from last_successful_exp.experiment_workspace should have been performed
    assert result_exp.experiment_workspace.injected_from == last_ws.file_dict, "The new experiment workspace should have injected files from the last successful experiment"
