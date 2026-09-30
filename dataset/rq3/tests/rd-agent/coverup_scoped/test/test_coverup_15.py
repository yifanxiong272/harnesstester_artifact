# file: rdagent/scenarios/data_science/proposal/exp_gen/merge.py:148-236
# asked: {"lines": [154, 156, 157, 158, 159, 161, 163, 164, 166, 168, 169, 170, 171, 172, 174, 175, 176, 177, 178, 179, 183, 184, 185, 188, 189, 190, 191, 192, 193, 197, 198, 199, 200, 202, 203, 204, 207, 208, 209, 210, 211, 216, 217, 218, 219, 220, 222, 223, 225, 227, 228, 229, 230, 231, 232, 233, 235], "branches": [[156, 157], [156, 163], [170, 171], [170, 183], [171, 172], [171, 174], [188, 189], [188, 197], [199, 200], [199, 202], [222, 223], [222, 225]]}
# gained: {"lines": [154, 156, 157, 158, 159, 161, 163, 164, 166, 168, 169, 170, 171, 172, 174, 175, 176, 177, 178, 179, 183, 184, 185, 188, 189, 190, 191, 192, 193, 197, 198, 199, 200, 202, 203, 204, 207, 208, 209, 210, 211, 216, 217, 218, 219, 220, 222, 223, 225, 227, 228, 229, 230, 231, 232, 233, 235], "branches": [[156, 157], [156, 163], [170, 171], [170, 183], [171, 172], [171, 174], [188, 189], [188, 197], [199, 200], [222, 223], [222, 225]]}

import pytest

import rdagent.scenarios.data_science.proposal.exp_gen.merge as merge
import rdagent.scenarios.data_science.proposal.exp_gen.proposal as proposal_mod


# Helpers for fake templating and simple serialization
def jsonable(obj):
    if isinstance(obj, dict):
        return "{" + ",".join(f"{k}={jsonable(v)}" for k, v in sorted(obj.items())) + "}"
    if isinstance(obj, (list, tuple)):
        return "[" + ",".join(jsonable(x) for x in obj) + "]"
    if obj is None:
        return "None"
    if isinstance(obj, str):
        return obj
    return repr(obj)


class FakeTemplate:
    def __init__(self, key):
        self.key = key
        self.calls = []

    def r(self, **kwargs):
        self.calls.append(kwargs)
        return f"TEMPLATE:{self.key}:{jsonable(kwargs)}"


class FakeDSSetting:
    def __init__(self, max_sota_retrieved_num=4, coder_on_whole_pipeline=True, enable_knowledge_base=True):
        self.max_sota_retrieved_num = max_sota_retrieved_num
        self.coder_on_whole_pipeline = coder_on_whole_pipeline
        self.enable_knowledge_base = enable_knowledge_base


class FakeWorkspace:
    def __init__(self, file_dict=None):
        self.file_dict = file_dict or {}


class FakeExperiment:
    def __init__(self, name):
        self.name = name
        self.experiment_workspace = FakeWorkspace()


class FakeFeedback:
    def __init__(self, name):
        self.name = name


class FakeKnowledgeBase:
    def __init__(self):
        self.updated = False
        self.args = None

    def update_pickled_problem(self, all_problems, pickled_problem_name):
        self.updated = True
        self.args = (all_problems, pickled_problem_name)


class FakeScenario:
    def __init__(self, desc="SCENARIO_DESC"):
        self.desc = desc
        self.last_eda = None

    def get_scenario_all_desc(self, eda_output=None):
        self.last_eda = eda_output
        return f"SCENARIO:{eda_output}"


class FakeTrace:
    def __init__(self, current_selection=(1,), leaves=(1, 2), sota_for_current=None, after_init_list=None, hist=None):
        self.current_selection = tuple(current_selection)
        self._leaves = list(leaves)
        self._sota_for_current = sota_for_current
        self._after_init = after_init_list or []
        self.hist = hist or []
        self.knowledge_base = FakeKnowledgeBase()
        self.scen = FakeScenario()

    def sota_experiment_fb(self, selection):
        if tuple(selection) == tuple(self.current_selection):
            return self._sota_for_current
        return None

    def get_leaves(self):
        return list(self._leaves)

    def experiment_and_feedback_list_after_init(self, return_type, search_type, selection, max_retrieve_num):
        return list(self._after_init)


# Monkeypatch factory for merge.T
def make_fake_T_factory(monkeypatch):
    instances = {}

    def factory(key):
        inst = FakeTemplate(key)
        instances[key] = inst
        return inst

    monkeypatch.setattr(merge, "T", factory)
    return instances


# Fake APIBackend for DSProposalV2ExpGen.__init__
class FakeAPIBackend:
    def supports_response_schema(self):
        return False


def test_gen_with_sota_and_success_list(monkeypatch):
    # Arrange: DS settings
    fake_setting = FakeDSSetting(max_sota_retrieved_num=8, coder_on_whole_pipeline=True, enable_knowledge_base=True)
    monkeypatch.setattr(merge, "DS_RD_SETTING", fake_setting)

    # Patch APIBackend used in DSProposalV2ExpGen to avoid side effects
    monkeypatch.setattr(proposal_mod, "APIBackend", FakeAPIBackend)

    # Patch T factory
    make_fake_T_factory(monkeypatch)

    # Prepare trace with sota for current selection and after_init results when checking other leaves
    exp0 = FakeExperiment("exp_sota")
    exp0.experiment_workspace.file_dict["EDA.md"] = "EDA CONTENT"

    after_init = [("expA", "fbA"), ("expB", "fbB"), ("expA", "fbA")]  # include duplicate to test set()
    trace = FakeTrace(current_selection=(1,), leaves=(1, 2), sota_for_current=[exp0], after_init_list=after_init, hist=[])

    # Create a subclass that overrides methods used by gen to make assertions
    class DummyGen(merge.ExpGen2Hypothesis):
        def hypothesis_gen(self, component_desc, exp_feedback_list_desc, sota_exp_desc, enable_idea_pool, pipeline):
            assert isinstance(component_desc, str) and component_desc.startswith("TEMPLATE:")
            # exp_feedback_list_desc should contain 'type=success' because we passed type="success" in T.r
            assert isinstance(exp_feedback_list_desc, str) and "type=success" in exp_feedback_list_desc
            assert sota_exp_desc.startswith("TEMPLATE:")
            return {"h1": 1}

        def hypothesis_rank(self, hypothesis_dict, problem_dict, selected_idx):
            assert hypothesis_dict == {"h1": 1}
            assert isinstance(problem_dict, dict) and problem_dict == {}
            return ("pickled_name", {"name": "new_hypothesis"})

        def task_gen(self, component_desc, scenario_desc, sota_exp_desc, sota_exp, hypotheses, hypotheses_candidates, pipeline, failed_exp_feedback_list_desc):
            assert isinstance(component_desc, str) and component_desc.startswith("TEMPLATE:")
            assert isinstance(scenario_desc, str) and scenario_desc.startswith("SCENARIO:")
            # since sota was provided, sota_exp should be our exp0
            assert sota_exp is exp0
            assert hypotheses == [{"name": "new_hypothesis"}]
            assert hypotheses_candidates == [{"name": "new_hypothesis"}]
            assert pipeline == fake_setting.coder_on_whole_pipeline
            return "TASK_OK"

    gen = DummyGen(FakeScenario())

    # Act
    result = gen.gen(trace)

    # Assert result and that knowledge base was updated
    assert result == "TASK_OK"
    assert trace.knowledge_base.updated is True
    assert trace.knowledge_base.args[1] == "pickled_name"


def test_gen_without_sota_and_no_success(monkeypatch):
    # Arrange: DS setting where knowledge base is disabled
    fake_setting = FakeDSSetting(max_sota_retrieved_num=4, coder_on_whole_pipeline=False, enable_knowledge_base=False)
    monkeypatch.setattr(merge, "DS_RD_SETTING", fake_setting)

    # Patch APIBackend
    monkeypatch.setattr(proposal_mod, "APIBackend", FakeAPIBackend)

    # Patch T factory
    make_fake_T_factory(monkeypatch)

    # Prepare trace: no sota for current selection, no after_init results
    hist_entry = ("exp_hist", "fb_hist")
    trace = FakeTrace(current_selection=(1,), leaves=(1,), sota_for_current=None, after_init_list=[], hist=[hist_entry])

    class DummyGen2(merge.ExpGen2Hypothesis):
        def get_exp_index(self, trace_arg):
            # return 0 so code will try trace.sota_experiment_fb(selection=(0,))
            return 0

        def hypothesis_gen(self, component_desc, exp_feedback_list_desc, sota_exp_desc, enable_idea_pool, pipeline):
            # exp_feedback_list_desc should be a TEMPLATE string produced by T
            assert isinstance(exp_feedback_list_desc, str) and exp_feedback_list_desc.startswith("TEMPLATE:")
            assert sota_exp_desc == ""  # since no sota
            return {"h2": 2}

        def hypothesis_rank(self, hypothesis_dict, problem_dict, selected_idx):
            assert hypothesis_dict == {"h2": 2}
            return ("pk2", {"name": "new2"})

        def task_gen(self, component_desc, scenario_desc, sota_exp_desc, sota_exp, hypotheses, hypotheses_candidates, pipeline, failed_exp_feedback_list_desc):
            assert sota_exp is None
            assert hypotheses == [{"name": "new2"}]
            assert pipeline == fake_setting.coder_on_whole_pipeline
            assert scenario_desc.startswith("SCENARIO:None")
            return "TASK_NO_SOTA"

    gen = DummyGen2(FakeScenario())

    # Act
    result = gen.gen(trace)

    # Assert
    assert result == "TASK_NO_SOTA"
    # Because enable_knowledge_base False, knowledge base should not be updated
    assert trace.knowledge_base.updated is False
