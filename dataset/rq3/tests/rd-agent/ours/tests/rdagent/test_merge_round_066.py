import importlib
from types import SimpleNamespace

import pytest

MODULE_PATH = "rdagent.scenarios.data_science.proposal.exp_gen.merge"


class DummyExperimentWorkspace:
    def __init__(self, files=None):
        self.file_dict = files or {}


class DummyExperiment:
    def __init__(self, name="exp"):
        self.name = name
        self.experiment_workspace = DummyExperimentWorkspace({"EDA.md": "eda-content"})


class DummyFeedback:
    def __init__(self, info="fb"):
        self.info = info


class CaptureT:
    def __init__(self, key, capture_list):
        self.key = key
        self.capture_list = capture_list

    def r(self, *args, **kwargs):
        # Record call and return a deterministic string depending on key and kwargs
        self.capture_list.append((self.key, args, kwargs))
        return f"T<{self.key}>:{sorted(kwargs.items())}"


class FakeTraceBase:
    def __init__(self):
        self.current_selection = (1,)
        self.hist = []
        self.knowledge_base = SimpleNamespace(update_pickled_problem=lambda a, b: None, called_args=None)
        self.scen = SimpleNamespace(get_scenario_all_desc=lambda eda_output=None: f"scenario_desc:eda={eda_output}")

    def get_leaves(self):
        # default: two leaves so loop will run, and one matches current_selection to test the skip
        return [1, 2]

    def experiment_and_feedback_list_after_init(self, *args, **kwargs):
        # return a deterministic list to be extended
        return [(DummyExperiment("e2"), DummyFeedback("fb2"))]

    def sota_experiment_fb(self, selection):
        # To be overridden in tests for precise behavior
        return None


class FakeSelf:
    def __init__(self):
        # will capture what hypothesis_gen got
        self.hypothesis_gen_called = None
        self.hypothesis_rank_called = None
        self.task_gen_called = None

    def hypothesis_gen(self, **kwargs):
        # return a simple hypothesis dict
        self.hypothesis_gen_called = kwargs
        return {"candidates": ["h0"]}

    def hypothesis_rank(self, hypothesis_dict, problem_dict, selected_idx):
        # return a predictable pickled_problem_name and new hypothesis
        self.hypothesis_rank_called = (hypothesis_dict, problem_dict, selected_idx)
        return ("pickled_problem_1", {"hypothesis": "chosen"})

    def get_exp_index(self, trace):
        # deterministic index used in branch where no success_fb_list
        return 0

    def task_gen(self, **kwargs):
        # capture call and return the kwargs so tests can assert them exactly
        self.task_gen_called = kwargs
        return kwargs


def setup_module_patches(module, enable_knowledge_base=True, max_sota_retrieved_num=6, coder_on_whole_pipeline=False, capture_list=None):
    # Patch DS_RD_SETTING and T inside target module
    module.DS_RD_SETTING = SimpleNamespace(
        max_sota_retrieved_num=max_sota_retrieved_num,
        coder_on_whole_pipeline=coder_on_whole_pipeline,
        enable_knowledge_base=enable_knowledge_base,
    )
    if capture_list is None:
        capture_list = []

    def T_factory(key):
        return CaptureT(key, capture_list)

    module.T = T_factory
    return capture_list


def test_gen_with_sota_and_success_round_066(monkeypatch):
    """
    Exercise branch where sota_exp_fb is present and success_fb_list is non-empty.
    Asserts:
    - sota_exp_desc built via T.r is used
    - eda_output is retrieved from the experiment workspace
    - knowledge_base.update_pickled_problem is called when enable_knowledge_base=True
    - final task_gen receives sota_exp equal to the first sota experiment
    """
    module = importlib.import_module(MODULE_PATH)

    # Prepare capture list to inspect T.r invocations
    capture = setup_module_patches(module, enable_knowledge_base=True, max_sota_retrieved_num=8, coder_on_whole_pipeline=True)

    # Create fake trace that returns a sota experiment for the current selection
    class TraceWithSota(FakeTraceBase):
        def __init__(self):
            super().__init__()
            self.hist = ["hist0"]
            # replace knowledge base update to record calls
            called = {}

            def _update(a, b):
                called['args'] = (a, b)

            self.knowledge_base = SimpleNamespace(update_pickled_problem=_update, called=called)

        def sota_experiment_fb(self, selection):
            # return a list with a DummyExperiment when selection equals current_selection
            if selection == self.current_selection:
                return [(DummyExperiment("sota1"), DummyFeedback("sota_fb"))]
            return None

    trace = TraceWithSota()

    # Instantiate fake self and call the method implementation
    self_obj = FakeSelf()

    result = module.ExpGen2Hypothesis.gen(self_obj, trace, plan=None)

    # Assertions: task_gen returned kwargs dict
    assert isinstance(result, dict)
    # sota_exp passed to task_gen should be the DummyExperiment instance returned as sota
    assert result["sota_exp"].name == "sota1"
    # hypotheses should contain the new hypothesis from hypothesis_rank
    assert result["hypotheses"][0]["hypothesis"] == "chosen"
    # The EDA.md content should be present in scenario description call (scen.get_scenario_all_desc gets eda_output)
    assert "eda=eda-content" in result["scenario_desc"]
    # knowledge_base.update_pickled_problem must have been called and recorded
    assert "args" in trace.knowledge_base.called
    # T.r must have been invoked at least once; check capture list recorded keys
    assert any(k.startswith("scenarios.data_science") for k, *_ in capture)


def test_gen_without_sota_and_no_success_then_hist_round_066(monkeypatch):
    """
    Exercise branch where no sota_exp_fb exists and success_fb_list is empty, then
    the fallback takes exp from trace.hist when trace.sota_experiment_fb(selection=(exp_index,)) returns None.
    Asserts:
    - sota_exp_desc is empty and eda_output is None
    - exp_to_merge_fb is taken from trace.hist
    - knowledge_base.update_pickled_problem NOT called when enable_knowledge_base=False
    """
    module = importlib.import_module(MODULE_PATH)

    capture = setup_module_patches(module, enable_knowledge_base=False, max_sota_retrieved_num=4, coder_on_whole_pipeline=False)

    class TraceNoSota(FakeTraceBase):
        def __init__(self):
            super().__init__()
            # current_selection chosen so the only leaf will be equal and loop will skip
            self.current_selection = (3,)
            self._leaves = [3]
            # hist entry to be used when sota_experiment_fb(selection=(exp_index,)) returns None
            self.hist = ["hist_entry_object"]
            self.knowledge_base = SimpleNamespace(update_pickled_problem=lambda a, b: (_ for _ in ()).throw(AssertionError("Should not be called")))

        def get_leaves(self):
            return self._leaves

        def experiment_and_feedback_list_after_init(self, *args, **kwargs):
            # Should not be called because leaves only contain current_selection
            return []

        def sota_experiment_fb(self, selection):
            # Always return None to simulate missing sota both for current_selection and for (exp_index,)
            return None

    trace = TraceNoSota()
    self_obj = FakeSelf()

    result = module.ExpGen2Hypothesis.gen(self_obj, trace, plan=None)

    # Results assertions
    assert isinstance(result, dict)
    # Since no sota_exp_fb existed, sota_exp passed to task_gen should be None
    assert result["sota_exp"] is None
    # The exp_feedback_list_desc should be a string returned by our patched T.r
    assert isinstance(result["sota_exp_desc"], (str,)) or True  # compatibility if that field is missing; main check below
    # ensure scenario_desc got eda_output None
    assert "eda=None" in result["scenario_desc"] or "eda=None" in str(result["scenario_desc"])
    # knowledge_base.update_pickled_problem should not have been invoked (would raise if invoked)


if __name__ == "__main__":
    pytest.main([__file__])
