# file: rdagent/scenarios/data_science/proposal/exp_gen/merge.py:276-349
# asked: {"lines": [282, 285, 286, 287, 289, 290, 291, 293, 294, 295, 298, 300, 301, 302, 303, 305, 306, 307, 310, 311, 312, 313, 315, 316, 317, 318, 319, 320, 324, 325, 326, 329, 331, 332, 333, 334, 335, 339, 340, 341, 342, 343, 347, 348, 349], "branches": [[286, 287], [286, 289], [300, 301], [300, 329], [302, 303], [302, 305], [315, 316], [315, 324], [347, 348], [347, 349]]}
# gained: {"lines": [282, 285, 286, 287, 289, 290, 291, 293, 294, 295, 298, 300, 301, 302, 303, 305, 306, 307, 310, 311, 312, 313, 315, 316, 317, 318, 319, 320, 324, 325, 326, 329, 331, 332, 333, 334, 335, 339, 340, 341, 342, 343, 347, 348, 349], "branches": [[286, 287], [286, 289], [300, 301], [300, 329], [302, 303], [315, 316], [315, 324], [347, 348]]}

import importlib
from types import SimpleNamespace

import pytest


class MockRendered:
    def __init__(self, key):
        self.key = key

    def r(self, **kwargs):
        # return a deterministic string including the key and sorted keys for easy assertions
        items = ",".join(f"{k}={kwargs[k]!r}" for k in sorted(kwargs.keys()))
        return f"rendered[{self.key}]({items})"


class MockPipelineTask:
    def __init__(self, description):
        self.description = description


class MockDSHypothesis:
    def __init__(self, component, hypothesis):
        self.component = component
        self.hypothesis = hypothesis


class MockGeneratedWorkspace:
    def __init__(self):
        self.injected = None

    def inject_code_from_file_dict(self, file_dict):
        # store a shallow copy to make sure mutation outside won't affect stored value
        self.injected = dict(file_dict) if file_dict is not None else None


class MockGeneratedExperiment:
    def __init__(self, pending_tasks_list=None, hypothesis=None):
        # emulate minimal DSExperiment used by gen()
        self.pending_tasks_list = pending_tasks_list
        self.hypothesis = hypothesis
        self.experiment_workspace = MockGeneratedWorkspace()


class FakePreviousExp:
    def __init__(self, workspace_dict):
        # In code they access .experiment_workspace on previous experiments and pass it to inject
        self.experiment_workspace = workspace_dict


class DummyTraceBase:
    def __init__(self, leaves, hist, sota_map=None, success_map=None):
        """
        leaves: list of ints
        hist: list where hist[i] is tuple(exp, fb)
        sota_map: dict from selection int -> tuple(exp, fb) or None to indicate sota_experiment_fb returns something
        success_map: dict from selection int -> list of (exp, fb) returned by experiment_and_feedback_list_after_init
        """
        self._leaves = leaves
        self.hist = hist
        self._sota_map = sota_map or {}
        self._success_map = success_map or {}

    def get_leaves(self):
        return list(self._leaves)

    def sota_experiment_fb(self, search_type="ancestors", selection=None):
        # selection expected to be a tuple like (i,)
        if selection is None:
            key = None
        else:
            key = selection[0]
        return self._sota_map.get(key, None)

    def experiment_and_feedback_list_after_init(self, return_type="sota", search_type="ancestors", selection=None, max_retrieve_num=None):
        key = selection[0] if selection else None
        return list(self._success_map.get(key, []))


@pytest.fixture(autouse=True)
def patch_merge_module(monkeypatch):
    # Import the module under test
    merge_mod = importlib.import_module("rdagent.scenarios.data_science.proposal.exp_gen.merge")

    # Patch external dependencies inside the module to lightweight mocks
    monkeypatch.setattr(merge_mod, "T", MockRendered)
    monkeypatch.setattr(merge_mod, "PipelineTask", MockPipelineTask)
    monkeypatch.setattr(merge_mod, "DSHypothesis", MockDSHypothesis)
    monkeypatch.setattr(merge_mod, "DSExperiment", MockGeneratedExperiment)

    # Provide a DS_RD_SETTING object with coder_on_whole_pipeline attribute (can be changed in tests)
    monkeypatch.setattr(merge_mod, "DS_RD_SETTING", SimpleNamespace(coder_on_whole_pipeline=False))

    yield merge_mod  # allow tests to receive module via fixture by re-importing


def test_gen_no_sota_and_no_success(monkeypatch):
    merge_mod = importlib.import_module("rdagent.scenarios.data_science.proposal.exp_gen.merge")

    # Prepare history entries: two previous experiments (for leaves 0 and 1)
    hist = [
        (FakePreviousExp({"file_a": "code_a"}), {"fb": "first"}),
        (FakePreviousExp({"file_b": "code_b"}), {"fb": "second"}),
    ]

    # Create a trace where sota_experiment_fb returns None for all selections
    trace = DummyTraceBase(leaves=[0, 1], hist=hist, sota_map={}, success_map={})

    # Instantiate MergeExpGen_MultiTrace with a dummy scen argument as required by ExpGen.__init__
    gen = merge_mod.MergeExpGen_MultiTrace(SimpleNamespace())
    exp = gen.gen(trace)

    # Assertions: returned object is our mocked DSExperiment
    assert isinstance(exp, MockGeneratedExperiment)
    # pending tasks list should be set and contain inner list with MockPipelineTask
    assert isinstance(exp.pending_tasks_list, list)
    assert len(exp.pending_tasks_list) == 1
    inner = exp.pending_tasks_list[0]
    assert isinstance(inner, list)
    assert isinstance(inner[0], MockPipelineTask)
    # Because sota_experiment_fb returned None and code falls back to hist[0], injection should have been called
    assert exp.experiment_workspace.injected == hist[0][0].experiment_workspace
    # The PipelineTask.description should include the rendered template string produced by MockRendered
    assert "rendered[" in inner[0].description
    # and should specifically include the multi_trace key used in the module
    assert "scenarios.data_science.proposal.exp_gen.merge:multi_trace" in inner[0].description


def test_gen_with_sota_and_success(monkeypatch):
    merge_mod = importlib.import_module("rdagent.scenarios.data_science.proposal.exp_gen.merge")

    # Set DS_RD_SETTING.coder_on_whole_pipeline True to ensure that branch passes pipeline param
    monkeypatch.setattr(merge_mod, "DS_RD_SETTING", SimpleNamespace(coder_on_whole_pipeline=True))

    # Prepare a SOTA previous experiment (for leaf 0) whose experiment_workspace is a dict to be injected
    sota_workspace = {"sota_code": "print('hello')"}
    sota_prev = FakePreviousExp(sota_workspace)

    # Prepare a second previous experiment (for leaf 1) for hist fallback if needed
    hist_entry = (FakePreviousExp({"other": "x"}), {"fb": "hist_fb"})

    # For leaf 1, we want experiment_and_feedback_list_after_init to return non-empty list -> success branch
    success_item = (FakePreviousExp({"succ": "y"}), {"fb": "succ_fb"})

    hist = [
        (FakePreviousExp({"should_not_be_used": "a"}), {"fb": "first"}),
        hist_entry,
    ]

    sota_map = {0: (sota_prev, {"fb": "sota_fb"}), 1: None}
    success_map = {1: [success_item]}

    trace = DummyTraceBase(leaves=[0, 1], hist=hist, sota_map=sota_map, success_map=success_map)

    gen = merge_mod.MergeExpGen_MultiTrace(SimpleNamespace())
    exp = gen.gen(trace)

    # The returned experiment should be our mocked DSExperiment
    assert isinstance(exp, MockGeneratedExperiment)
    # Because sota_exp_fb was provided, gen should have injected the sota workspace dict into the new experiment
    assert exp.experiment_workspace.injected == sota_workspace
    # Check pending tasks and that description contains rendered strings
    assert isinstance(exp.pending_tasks_list, list)
    inner = exp.pending_tasks_list[0]
    assert isinstance(inner[0], MockPipelineTask)
    desc = inner[0].description
    assert "rendered[" in desc
    # Confirm that the rendered description key for the generated multi_trace is present
    assert "scenarios.data_science.proposal.exp_gen.merge:multi_trace" in desc
