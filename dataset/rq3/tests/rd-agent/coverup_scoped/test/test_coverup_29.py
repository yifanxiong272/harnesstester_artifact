# file: rdagent/scenarios/data_science/proposal/exp_gen/merge.py:27-96
# asked: {"lines": [33, 34, 37, 38, 39, 40, 41, 42, 47, 48, 49, 51, 52, 53, 55, 56, 57, 60, 61, 63, 64, 65, 66, 67, 68, 72, 73, 74, 77, 78, 79, 80, 81, 82, 86, 87, 88, 89, 90, 94, 95, 96], "branches": [[38, 39], [38, 40], [41, 42], [41, 47], [63, 64], [63, 72], [94, 95], [94, 96]]}
# gained: {"lines": [33, 34, 37, 38, 39, 40, 41, 42, 47, 48, 49, 51, 52, 53, 55, 56, 57, 60, 61, 63, 64, 65, 66, 67, 68, 72, 73, 74, 77, 78, 79, 80, 81, 82, 86, 87, 88, 89, 90, 94, 95, 96], "branches": [[38, 39], [38, 40], [41, 42], [41, 47], [63, 64], [63, 72], [94, 95]]}

import importlib
import pytest


class DummyTpl:
    def __init__(self, key):
        self.key = key

    def r(self, **kwargs):
        # Return a string that contains the key and the kwarg keys so tests can assert composition.
        return f"TEMPLATE[{self.key}]::{sorted(list(kwargs.keys()))}"


class DummyPipelineTask:
    def __init__(self, *, description):
        self.description = description


class DummyDSHypothesis:
    def __init__(self, component, hypothesis):
        self.component = component
        self.hypothesis = hypothesis


class DummyExperimentWorkspace:
    def __init__(self):
        self.injected = None

    def inject_code_from_file_dict(self, d):
        # record the injected dict for assertions
        self.injected = d.copy() if isinstance(d, dict) else d


class DummyDSExperiment:
    def __init__(self, pending_tasks_list, hypothesis):
        self.pending_tasks_list = pending_tasks_list
        self.hypothesis = hypothesis
        self.experiment_workspace = DummyExperimentWorkspace()


class DummySetting:
    def __init__(self):
        self.coder_on_whole_pipeline = "DUMMY_PIPELINE_SETTING"


class FakeExp:
    def __init__(self, name, workspace_dict=None):
        self.name = name
        self.experiment_workspace = workspace_dict or {"default": 1}


class FakeFeedback:
    def __init__(self, msg):
        self.msg = msg


class FakeTrace:
    def __init__(self, leaves, hist_map, sota_map=None, success_list=None):
        # leaves: list of ints
        # hist_map: dict leaf->(exp, fb)
        # sota_map: dict leaf->(exp, fb) or None entries
        # success_list: list returned by experiment_and_feedback_list_after_init
        self._leaves = list(leaves)
        self.hist = dict(hist_map)
        self._sota_map = sota_map or {}
        self._success_list = list(success_list) if success_list is not None else []
        self.last_set_selection = None

    def get_leaves(self):
        return list(self._leaves)

    def set_current_selection(self, sel):
        self.last_set_selection = sel

    def sota_experiment_fb(self, selection):
        # selection is tuple
        leaf = selection[0]
        # Explicitly return what's in _sota_map, possibly None
        return self._sota_map.get(leaf, None)

    def experiment_and_feedback_list_after_init(self, return_type, search_type, selection):
        # ignore arguments; return configured success_list
        return list(self._success_list)


@pytest.fixture(autouse=True)
def monkeypatch_merge_module(monkeypatch):
    """
    Monkeypatch the merge module's external dependencies to deterministic fakes.
    This fixture is auto-used for each test in this module.
    """
    mod = importlib.import_module("rdagent.scenarios.data_science.proposal.exp_gen.merge")
    # Patch T, PipelineTask, DSExperiment, DSHypothesis, DS_RD_SETTING
    monkeypatch.setattr(mod, "T", lambda key: DummyTpl(key), raising=True)
    monkeypatch.setattr(mod, "PipelineTask", DummyPipelineTask, raising=True)
    monkeypatch.setattr(mod, "DSExperiment", DummyDSExperiment, raising=True)
    monkeypatch.setattr(mod, "DSHypothesis", DummyDSHypothesis, raising=True)
    monkeypatch.setattr(mod, "DS_RD_SETTING", DummySetting(), raising=True)
    yield
    # monkeypatch fixture will revert changes automatically


def test_merge_gen_with_sota_present_and_success_list_non_empty():
    mod = importlib.import_module("rdagent.scenarios.data_science.proposal.exp_gen.merge")
    MergeExpGen = getattr(mod, "MergeExpGen")

    # Prepare fake experiments and feedbacks
    exp0 = FakeExp("exp0", workspace_dict={"file0.py": "print('hello')"})
    fb0 = FakeFeedback("fb0")
    sota_tuple = (exp0, fb0)

    exp1 = FakeExp("exp1", workspace_dict={"file1.py": "print('world')"})
    fb1 = FakeFeedback("fb1")
    merge_tuple = (exp1, fb1)

    # build trace: get_leaves returns [10,20]
    # sota_map contains entry for leaves[0] so sota_experiment_fb returns non-None
    trace = FakeTrace(
        leaves=[10, 20],
        hist_map={10: sota_tuple, 20: merge_tuple},
        sota_map={10: sota_tuple, 20: merge_tuple},
        success_list=[("s1",), ("s2",)],
    )

    gen = MergeExpGen(object())
    exp_obj = gen.gen(trace)

    # Assertions: selection was set to first leaf
    assert trace.last_set_selection == (10,)

    # exp_obj should be DummyDSExperiment with correct pending_tasks_list structure
    assert isinstance(exp_obj, DummyDSExperiment)
    assert isinstance(exp_obj.pending_tasks_list, list)
    # one task inside nested list
    assert len(exp_obj.pending_tasks_list) == 1
    assert len(exp_obj.pending_tasks_list[0]) == 1
    task = exp_obj.pending_tasks_list[0][0]
    assert isinstance(task, DummyPipelineTask)
    # description produced by our dummy template includes the template key
    assert "scenarios.data_science.proposal.exp_gen.merge:task" in task.description
    # Because we used DummyTpl.r, the description contains the names of kwargs passed (list)
    assert "sota_exp_desc" in task.description and "exp_to_merge_desc" in task.description

    # The workspace of exp_obj should have recorded injected dict from sota_exp_fb[0].experiment_workspace
    assert exp_obj.experiment_workspace.injected == exp0.experiment_workspace


def test_merge_gen_with_sota_none_and_exp_to_merge_from_hist_and_no_success_list():
    mod = importlib.import_module("rdagent.scenarios.data_science.proposal.exp_gen.merge")
    MergeExpGen = getattr(mod, "MergeExpGen")

    # Prepare fake experiments and feedbacks
    exp0 = FakeExp("exp0_hist", workspace_dict={"a.py": "code_a"})
    fb0 = FakeFeedback("fb0_hist")
    hist0 = (exp0, fb0)

    exp1 = FakeExp("exp1_hist", workspace_dict={"b.py": "code_b"})
    fb1 = FakeFeedback("fb1_hist")
    hist1 = (exp1, fb1)

    # Create a trace where sota_experiment_fb returns None for both leaves, so hist used
    trace = FakeTrace(
        leaves=[1, 2],
        hist_map={1: hist0, 2: hist1},
        sota_map={1: None, 2: None},
        success_list=[],
    )

    gen = MergeExpGen(object())
    exp_obj = gen.gen(trace)

    # Ensure selection overridden
    assert trace.last_set_selection == (1,)

    # Ensure pending tasks structure and content
    assert isinstance(exp_obj.pending_tasks_list, list)
    task = exp_obj.pending_tasks_list[0][0]
    assert "scenarios.data_science.proposal.exp_gen.merge:task" in task.description
    # Because no success list, the description building for exp_to_merge_fb_desc used 'describe.feedback'
    # Our DummyTpl r returns a string containing the kwargs keys; check presence
    assert "exp_to_merge_fb_desc" in task.description

    # Ensure injection used the hist entry for leaf 1
    assert exp_obj.experiment_workspace.injected == exp0.experiment_workspace
