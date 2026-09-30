# file: rdagent/scenarios/data_science/proposal/exp_gen/proposal.py:1302-1501
# asked: {"lines": [1307, 1308, 1309, 1311, 1312, 1314, 1315, 1316, 1317, 1321, 1322, 1324, 1326, 1327, 1329, 1330, 1333, 1334, 1338, 1339, 1340, 1341, 1345, 1346, 1347, 1348, 1349, 1351, 1352, 1354, 1357, 1358, 1360, 1361, 1363, 1365, 1367, 1370, 1371, 1372, 1373, 1374, 1375, 1376, 1377, 1381, 1382, 1383, 1384, 1385, 1386, 1387, 1391, 1394, 1395, 1396, 1397, 1398, 1399, 1400, 1402, 1403, 1404, 1405, 1406, 1408, 1409, 1410, 1411, 1412, 1413, 1416, 1417, 1418, 1419, 1420, 1421, 1422, 1425, 1426, 1429, 1430, 1432, 1433, 1434, 1435, 1436, 1437, 1438, 1440, 1443, 1444, 1445, 1446, 1447, 1448, 1449, 1450, 1451, 1453, 1454, 1455, 1456, 1458, 1461, 1462, 1463, 1464, 1467, 1468, 1469, 1471, 1472, 1474, 1476, 1477, 1478, 1482, 1483, 1485, 1486, 1487, 1488, 1489, 1491, 1492, 1493, 1495, 1496, 1497, 1498, 1499, 1500], "branches": [[1308, 1309], [1308, 1311], [1311, 1312], [1311, 1314], [1321, 1322], [1321, 1324], [1326, 1327], [1326, 1329], [1351, 1352], [1351, 1354], [1357, 1358], [1357, 1365], [1358, 1360], [1358, 1363], [1381, 1382], [1381, 1391], [1408, 1409], [1408, 1425], [1416, 1417], [1416, 1425], [1418, 1419], [1418, 1421], [1419, 1418], [1419, 1420], [1421, 1422], [1421, 1425], [1425, 1426], [1425, 1458], [1461, 1462], [1461, 1476], [1482, 1483], [1482, 1485]]}
# gained: {"lines": [1307, 1308, 1309, 1311, 1312, 1314, 1315, 1316, 1317, 1321, 1324, 1326, 1327, 1330, 1333, 1334, 1338, 1339, 1340, 1341, 1345, 1346, 1347, 1348, 1349, 1351, 1352, 1357, 1358, 1360, 1361, 1365, 1367, 1370, 1371, 1372, 1373, 1374, 1375, 1376, 1377, 1381, 1382, 1383, 1384, 1385, 1386, 1387, 1391, 1394, 1395, 1396, 1397, 1398, 1399, 1400, 1402, 1403, 1404, 1405, 1406, 1408, 1409, 1410, 1411, 1412, 1413, 1416, 1417, 1418, 1419, 1420, 1421, 1422, 1425, 1426, 1429, 1430, 1432, 1433, 1434, 1435, 1436, 1437, 1438, 1440, 1443, 1444, 1445, 1446, 1447, 1448, 1449, 1450, 1451, 1453, 1458, 1461, 1462, 1463, 1464, 1467, 1468, 1469, 1471, 1472, 1474, 1476, 1477, 1478, 1482, 1483, 1485, 1486, 1487, 1488, 1489, 1491, 1492, 1493, 1495, 1496, 1497, 1498, 1499, 1500], "branches": [[1308, 1309], [1308, 1311], [1311, 1312], [1311, 1314], [1321, 1324], [1326, 1327], [1351, 1352], [1357, 1358], [1357, 1365], [1358, 1360], [1381, 1382], [1408, 1409], [1408, 1425], [1416, 1417], [1418, 1419], [1418, 1421], [1419, 1418], [1419, 1420], [1421, 1422], [1421, 1425], [1425, 1426], [1425, 1458], [1461, 1462], [1461, 1476], [1482, 1483]]}

import types
from types import SimpleNamespace

import pytest


MODULE_PATH = "rdagent.scenarios.data_science.proposal.exp_gen.proposal"


def make_fake_T(monkeypatch, mod):
    """
    Create a fake T factory to be injected into the module. It returns an object with:
    - r(...) -> returns a simple string that includes the name
    - .template dict for the component_description case
    """
    class FakeTemplate:
        def __init__(self, key):
            self.key = key
            # Provide a template dict expected by code when using component_description
            self.template = {"c1": "Component 1", "c2": "Component 2"}

        def r(self, *args, **kwargs):
            # Return a string that includes the key so tests can detect invocation.
            return f"rendered({self.key})"

    def T_factory(key):
        return FakeTemplate(key)

    monkeypatch.setattr(mod, "T", T_factory, raising=False)


class DummyExperiment:
    def __init__(self, file_dict=None):
        if file_dict is None:
            file_dict = {}
        self.experiment_workspace = SimpleNamespace(file_dict=file_dict)


class DummyFeedback:
    pass


class DummyKB:
    def __init__(self):
        self.sample_called = False
        self.update_called_with = None

    def sample_ideas(self, problems, scenario_desc, exp_feedback_list_desc, sota_exp_desc, competition_desc):
        self.sample_called = True
        # Just append a marker to problems to indicate it was sampled
        new_problems = dict(problems)
        new_problems["_kb_sampled"] = True
        return new_problems

    def update_pickled_problem(self, all_problems, pickled_problem_name):
        self.update_called_with = (all_problems, pickled_problem_name)


class DummyTrace:
    def __init__(self, *, hist=None, current_selection=None, is_new_tree=False, sibling_exps=None, should_inject=True, parent_exps=None, fb_list_all=None, fb_list_failed=None, sota_fb=None):
        self.hist = [] if hist is None else hist
        self.current_selection = [] if current_selection is None else current_selection
        self._is_new_tree = is_new_tree
        self._sibling_exps = sibling_exps or []
        self._should_inject = should_inject
        self._parent_exps = parent_exps or []
        self._fb_list_all = [] if fb_list_all is None else fb_list_all
        self._fb_list_failed = [] if fb_list_failed is None else fb_list_failed
        self._sota_fb = sota_fb
        self.knowledge_base = DummyKB()

    def sota_experiment_fb(self):
        # Return predefined SOTA pair or None
        return self._sota_fb

    def experiment_and_feedback_list_after_init(self, return_type="all"):
        if return_type == "all":
            return self._fb_list_all
        elif return_type == "failed":
            return self._fb_list_failed
        else:
            return []

    def get_sibling_exps(self):
        return self._sibling_exps

    def should_inject_diversity(self):
        return self._should_inject

    def get_parent_exps(self):
        return self._parent_exps

    def is_selection_new_tree(self):
        return self._is_new_tree


def import_module():
    import importlib

    return importlib.import_module(MODULE_PATH)


def make_proposal(monkeypatch):
    """
    Create a DSProposalV2ExpGen instance with many internal methods patched to
    predictable behaviors for testing.
    """
    mod = import_module()

    # Patch APIBackend used in DSProposalV2ExpGen.__init__ to avoid heavy behavior
    class DummyAPIBackend:
        def supports_response_schema(self):
            return False

    # Ensure the APIBackend symbol in the module is our dummy (add or replace)
    monkeypatch.setattr(mod, "APIBackend", DummyAPIBackend, raising=False)

    make_fake_T(monkeypatch, mod)

    # patch DS_RD_SETTING default container
    ds_settings = SimpleNamespace(
        coder_on_whole_pipeline=False,
        enable_inject_diverse=False,
        enable_knowledge_base=False,
        enable_hypo_critique_rewrite=False,
        llm_select_hypothesis=False,
    )
    monkeypatch.setattr(mod, "DS_RD_SETTING", ds_settings, raising=False)

    # Ensure draft_exp_in_decomposition exists in module; default returns None
    monkeypatch.setattr(mod, "draft_exp_in_decomposition", lambda scen, trace: None, raising=False)

    # Create a minimal scen object required by ExpGen.__init__
    def get_scenario_all_desc(eda_output=None):
        return f"scenario_desc:{eda_output}"

    def get_competition_full_desc():
        return "competition_desc"

    dummy_scen = SimpleNamespace(get_scenario_all_desc=get_scenario_all_desc, get_competition_full_desc=get_competition_full_desc)

    # Import class and instantiate with scen
    DSProposal = getattr(mod, "DSProposalV2ExpGen")
    proposal = DSProposal(dummy_scen)
    return mod, proposal, ds_settings


def test_gen_early_return_draft(monkeypatch):
    """
    When coder_on_whole_pipeline is False and draft_exp_in_decomposition returns a draft,
    gen should return that draft directly (lines ~1307-1309).
    """
    mod, proposal, ds_settings = make_proposal(monkeypatch)

    # configure settings so pipeline False
    ds_settings.coder_on_whole_pipeline = False

    # create a dummy draft experiment to be returned
    draft = DummyExperiment({"some": "file"})
    # patch draft_exp_in_decomposition to return draft
    monkeypatch.setattr(mod, "draft_exp_in_decomposition", lambda scen, trace: draft, raising=False)

    # Create a minimal trace
    trace = DummyTrace()

    result = proposal.gen(trace, plan=None)
    assert result is draft


def test_gen_pipeline_true_with_llm_and_critique_rewrite(monkeypatch):
    """
    Test the pipeline=True branch, exercising LLM selection and the critique/rewrite path
    including knowledge base sampling, inject_diverse, sibling_exp handling, and task_gen return.
    This covers many lines between 1311 and 1474 and onwards.
    """
    mod, proposal, ds_settings = make_proposal(monkeypatch)

    # Set pipeline True and other settings to exercise branches
    ds_settings.coder_on_whole_pipeline = True
    ds_settings.enable_knowledge_base = True
    ds_settings.enable_hypo_critique_rewrite = True
    ds_settings.llm_select_hypothesis = True
    ds_settings.enable_inject_diverse = True

    # Create a trace that has history to trigger critique/rewrite, and empty current_selection to trigger inject_diverse True
    sibling_exp = [DummyExperiment({"model.py": "content"})]
    trace = DummyTrace(hist=[1, 2], current_selection=[], is_new_tree=False, sibling_exps=sibling_exp,
                       should_inject=True, parent_exps=["parent"], fb_list_all=[("e", "f")], fb_list_failed=[],
                       sota_fb=(DummyExperiment({"EDA.md": "eda"}), DummyFeedback()))

    # Patch identify_problem to return a dict of problems
    called = {}
    def fake_identify_problem(**kwargs):
        called['identify_problem'] = True
        # return initial problems
        return {"p1": {"desc": "prob1"}}
    monkeypatch.setattr(proposal, "identify_problem", fake_identify_problem, raising=False)

    # hypothesis_gen returns two hypotheses
    def fake_hypothesis_gen(**kwargs):
        called['hypo_gen'] = kwargs
        return {"p1": {"component": "Comp", "hypothesis": "h1"}}
    monkeypatch.setattr(proposal, "hypothesis_gen", fake_hypothesis_gen, raising=False)

    # hypothesis_critique returns critiques
    def fake_hypothesis_critique(**kwargs):
        called['critique'] = True
        return {"p1": {"critique": "fix"}}
    monkeypatch.setattr(proposal, "hypothesis_critique", fake_hypothesis_critique, raising=False)

    # hypothesis_rewrite returns rewritten hypotheses
    def fake_hypothesis_rewrite(**kwargs):
        called['rewrite'] = True
        # return modified dict
        return {"p1": {"component": "Comp", "hypothesis": "h1_rewritten"}}
    monkeypatch.setattr(proposal, "hypothesis_rewrite", fake_hypothesis_rewrite, raising=False)

    # hypothesis_select_with_llm returns a valid selection dict
    def fake_select_with_llm(**kwargs):
        called['select_with_llm'] = True
        return {"component": "Comp", "hypothesis": "h1_rewritten"}
    monkeypatch.setattr(proposal, "hypothesis_select_with_llm", fake_select_with_llm, raising=False)

    # Patch task_gen to capture inputs and return a DummyExperiment
    captured = {}
    def fake_task_gen(**kwargs):
        captured.update(kwargs)
        return DummyExperiment({"task": "ok"})
    monkeypatch.setattr(proposal, "task_gen", fake_task_gen, raising=False)

    # Execute
    result = proposal.gen(trace, plan=None)

    # Assertions: ensure returned is from task_gen and various stages were called
    assert isinstance(result, DummyExperiment)
    assert called.get('identify_problem') is True
    assert called.get('hypo_gen') is not None
    assert called.get('critique') is True
    assert called.get('rewrite') is True
    assert called.get('select_with_llm') is True

    # Ensure knowledge base sampling and update were used
    assert trace.knowledge_base.sample_called is True
    # update_pickled_problem should be called because enable_knowledge_base True
    assert trace.knowledge_base.update_called_with is not None
    # task_gen should have been called with 'hypotheses' key
    assert "hypotheses" in captured
    # Since trace.is_selection_new_tree() is False, hypotheses should be a list with a single hypothesis
    assert isinstance(captured["hypotheses"], list) and len(captured["hypotheses"]) == 1


def test_gen_pipeline_false_pop_ensemble_and_rank_update_kb_and_task_gen(monkeypatch):
    """
    Test pipeline=False branch, ensure Ensemble hypotheses are popped when sota model count <=1,
    hypothesis_rank is used (llm_select_hypothesis False), knowledge base update called,
    and task_gen invoked with hypotheses_candidates without 'Ensemble'.
    This covers lines ~1408-1422, 1461-1478, 1482-1500.
    """
    mod, proposal, ds_settings = make_proposal(monkeypatch)

    # Configure settings
    ds_settings.coder_on_whole_pipeline = False  # go through non-pipeline branch
    ds_settings.enable_knowledge_base = True
    ds_settings.enable_hypo_critique_rewrite = False
    ds_settings.llm_select_hypothesis = False

    # Create a sota experiment with only one model file so the pop logic triggers
    sota_exp = DummyExperiment({"model.py": "content"})
    fb_to_sota = DummyFeedback()
    trace = DummyTrace(hist=[], current_selection=[1], is_new_tree=True, sibling_exps=[], should_inject=False,
                       parent_exps=[], fb_list_all=[("e1", "f1")], fb_list_failed=[], sota_fb=(sota_exp, fb_to_sota))

    # Patch draft_exp_in_decomposition to return None to avoid early return
    monkeypatch.setattr(mod, "draft_exp_in_decomposition", lambda scen, tr: None, raising=False)

    # identify_problem returns two problems, one with Ensemble
    def fake_identify_problem(current_sub_trace, scenario_desc, sota_exp_desc, exp_feedback_list_desc, inject_diverse, exp_gen_plan, sibling_exp):
        return {"p_ens": {"desc": "ens", "component": "Ensemble"}, "p_ok": {"desc": "ok", "component": "X"}}
    monkeypatch.setattr(proposal, "identify_problem", fake_identify_problem, raising=False)

    # hypothesis_gen returns hypothesis_dict containing an Ensemble
    def fake_hypo_gen(**kwargs):
        return {"p_ens": {"component": "Ensemble", "hypothesis": "h_ens"},
                "p_ok": {"component": "X", "hypothesis": "h_ok"}}
    monkeypatch.setattr(proposal, "hypothesis_gen", fake_hypo_gen, raising=False)

    # hypothesis_rank should be used; return pickled_problem_name and new hypothesis
    picked = {}
    def fake_hypothesis_rank(hypothesis_dict, problem_dict, selected_idx=None):
        picked['called_with'] = (dict(hypothesis_dict), dict(problem_dict))
        # return the non-ensemble choice
        return "p_ok", SimpleNamespace(component="X", hypothesis="h_ok")
    monkeypatch.setattr(proposal, "hypothesis_rank", fake_hypothesis_rank, raising=False)

    # get_all_hypotheses should return a list used as hypotheses_candidates
    def fake_get_all_hypotheses(problem_dict, hypothesis_dict):
        # Ensure Ensemble is not present (it should have been popped)
        assert all(v.get("component") != "Ensemble" for v in hypothesis_dict.values())
        return [SimpleNamespace(component=v.get("component"), hypothesis=v.get("hypothesis")) for v in hypothesis_dict.values()]
    monkeypatch.setattr(proposal, "get_all_hypotheses", fake_get_all_hypotheses, raising=False)

    # Patch task_gen to capture parameters and return an experiment
    captured = {}
    def fake_task_gen(**kwargs):
        captured.update(kwargs)
        return DummyExperiment({"final": "yes"})
    monkeypatch.setattr(proposal, "task_gen", fake_task_gen, raising=False)

    # Execute
    result = proposal.gen(trace, plan=None)

    # Assertions
    assert isinstance(result, DummyExperiment)
    # hypothesis_rank must be called
    assert "called_with" in picked
    # knowledge base update called
    assert trace.knowledge_base.update_called_with is not None
    # The hypotheses_candidates passed to task_gen should not include Ensemble
    assert "hypotheses_candidates" in captured
    assert all(getattr(h, "component", None) != "Ensemble" for h in captured["hypotheses_candidates"])
    # fb_to_sota_exp passed through
    assert captured.get("fb_to_sota_exp") is fb_to_sota
