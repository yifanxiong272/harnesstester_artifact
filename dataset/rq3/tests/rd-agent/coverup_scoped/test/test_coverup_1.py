# file: rdagent/scenarios/data_science/proposal/exp_gen/proposal.py:1302-1501
# asked: {"lines": [1307, 1308, 1309, 1311, 1312, 1314, 1315, 1316, 1317, 1321, 1322, 1324, 1326, 1327, 1329, 1330, 1333, 1334, 1338, 1339, 1340, 1341, 1345, 1346, 1347, 1348, 1349, 1351, 1352, 1354, 1357, 1358, 1360, 1361, 1363, 1365, 1367, 1370, 1371, 1372, 1373, 1374, 1375, 1376, 1377, 1381, 1382, 1383, 1384, 1385, 1386, 1387, 1391, 1394, 1395, 1396, 1397, 1398, 1399, 1400, 1402, 1403, 1404, 1405, 1406, 1408, 1409, 1410, 1411, 1412, 1413, 1416, 1417, 1418, 1419, 1420, 1421, 1422, 1425, 1426, 1429, 1430, 1432, 1433, 1434, 1435, 1436, 1437, 1438, 1440, 1443, 1444, 1445, 1446, 1447, 1448, 1449, 1450, 1451, 1453, 1454, 1455, 1456, 1458, 1461, 1462, 1463, 1464, 1467, 1468, 1469, 1471, 1472, 1474, 1476, 1477, 1478, 1482, 1483, 1485, 1486, 1487, 1488, 1489, 1491, 1492, 1493, 1495, 1496, 1497, 1498, 1499, 1500], "branches": [[1308, 1309], [1308, 1311], [1311, 1312], [1311, 1314], [1321, 1322], [1321, 1324], [1326, 1327], [1326, 1329], [1351, 1352], [1351, 1354], [1357, 1358], [1357, 1365], [1358, 1360], [1358, 1363], [1381, 1382], [1381, 1391], [1408, 1409], [1408, 1425], [1416, 1417], [1416, 1425], [1418, 1419], [1418, 1421], [1419, 1418], [1419, 1420], [1421, 1422], [1421, 1425], [1425, 1426], [1425, 1458], [1461, 1462], [1461, 1476], [1482, 1483], [1482, 1485]]}
# gained: {"lines": [1307, 1308, 1309, 1311, 1314, 1315, 1316, 1317, 1321, 1324, 1326, 1329, 1330, 1333, 1334, 1338, 1339, 1340, 1341, 1345, 1346, 1347, 1348, 1349, 1351, 1352, 1357, 1358, 1360, 1361, 1367, 1370, 1371, 1372, 1373, 1374, 1375, 1376, 1377, 1381, 1382, 1383, 1384, 1385, 1386, 1387, 1391, 1394, 1395, 1396, 1397, 1398, 1399, 1400, 1402, 1403, 1404, 1405, 1406, 1408, 1409, 1410, 1411, 1412, 1413, 1416, 1417, 1418, 1419, 1420, 1421, 1422, 1425, 1426, 1429, 1430, 1432, 1433, 1434, 1435, 1436, 1437, 1438, 1440, 1443, 1444, 1445, 1446, 1447, 1448, 1449, 1450, 1451, 1453, 1461, 1476, 1477, 1478, 1482, 1483, 1485, 1486, 1487, 1488, 1489, 1491, 1492, 1495, 1496, 1497, 1498, 1499, 1500], "branches": [[1308, 1309], [1308, 1311], [1311, 1314], [1321, 1324], [1326, 1329], [1351, 1352], [1357, 1358], [1358, 1360], [1381, 1382], [1408, 1409], [1416, 1417], [1418, 1419], [1418, 1421], [1419, 1418], [1419, 1420], [1421, 1422], [1421, 1425], [1425, 1426], [1461, 1476], [1482, 1483]]}

import types
import builtins
import pytest

import rdagent.scenarios.data_science.proposal.exp_gen.proposal as proposal_mod
from rdagent.app.data_science.conf import DS_RD_SETTING


class DummyTPL:
    def __init__(self, name):
        # simulate templates for component_description case
        self.template = {"compA": "Desc A", "compB": "Desc B"}

    def r(self, *args, **kwargs):
        return f"rendered:{args}:{kwargs}"


class DummyScenario:
    def get_scenario_all_desc(self, eda_output=None):
        return f"scenario_desc (eda={eda_output})"

    def get_competition_full_desc(self):
        return "competition_desc"


class DummyKB:
    def __init__(self):
        self.sample_called = False
        self.update_called = False
        self.last_update_args = None

    def sample_ideas(self, problems, scenario_desc, exp_feedback_list_desc, sota_exp_desc, competition_desc):
        self.sample_called = True
        # pretend to augment problems
        problems["kb_augmented"] = "kb"
        return problems

    def update_pickled_problem(self, all_problems, pickled_problem_name):
        self.update_called = True
        self.last_update_args = (all_problems, pickled_problem_name)


class FakeWorkspace:
    def __init__(self, file_dict):
        self.file_dict = file_dict


class FakeDSExp:
    def __init__(self, files=None):
        self.experiment_workspace = FakeWorkspace(files or {})


class DummyTrace:
    def __init__(self, kb, sota_exp):
        self.knowledge_base = kb
        self.hist = [1]  # non-empty to trigger some branches
        self.current_selection = []  # empty to trigger inject_diverse True when enable_inject_diverse is True
        self._sota_exp = sota_exp
        self._fb = "fb_to_sota"
        self._exp_and_fb_all = [("exp1", "fb1")]
        self._exp_and_fb_failed = []
        self.selection_new_tree = False

    def sota_experiment_fb(self):
        return (self._sota_exp, self._fb)

    def experiment_and_feedback_list_after_init(self, return_type="all"):
        if return_type == "all":
            return self._exp_and_fb_all
        else:
            return self._exp_and_fb_failed

    def get_parent_exps(self):
        return []

    def should_inject_diversity(self):
        return True

    def get_sibling_exps(self):
        return ["sib_exp"]

    def is_selection_new_tree(self):
        return self.selection_new_tree


def make_proposal_instance(scen):
    # create instance without calling __init__ to avoid ExpGen constructor dependencies
    inst = object.__new__(proposal_mod.DSProposalV2ExpGen)
    inst.scen = scen
    return inst


def test_gen_returns_draft_when_not_pipeline_and_draft_exists(monkeypatch):
    # Prepare: ensure coder_on_whole_pipeline False
    monkeypatch.setattr(DS_RD_SETTING, "coder_on_whole_pipeline", False, raising=False)

    # Provide a draft experiment to be returned by draft_exp_in_decomposition
    draft = FakeDSExp(files={"model_x.py": "content"})
    monkeypatch.setattr(proposal_mod, "draft_exp_in_decomposition", lambda scen, trace: draft)

    # Create minimal trace (not used because draft is returned)
    kb = DummyKB()
    trace = DummyTrace(kb, None)

    # Create instance
    inst = make_proposal_instance(DummyScenario())

    # Call gen and assert returned draft is as expected
    result = proposal_mod.DSProposalV2ExpGen.gen(inst, trace, plan=None)
    assert result is draft


def test_gen_full_flow_non_pipeline_with_kb_and_critique(monkeypatch):
    # Configure DS_RD_SETTING flags for this test
    monkeypatch.setattr(DS_RD_SETTING, "coder_on_whole_pipeline", False, raising=False)
    monkeypatch.setattr(DS_RD_SETTING, "enable_knowledge_base", True, raising=False)
    monkeypatch.setattr(DS_RD_SETTING, "enable_inject_diverse", True, raising=False)
    monkeypatch.setattr(DS_RD_SETTING, "enable_hypo_critique_rewrite", True, raising=False)
    monkeypatch.setattr(DS_RD_SETTING, "llm_select_hypothesis", False, raising=False)

    # Monkeypatch T to return predictable template and r()
    def T_factory(name):
        return DummyTPL(name)

    monkeypatch.setattr(proposal_mod, "T", T_factory, raising=False)

    # Ensure draft_exp_in_decomposition returns None so gen proceeds
    monkeypatch.setattr(proposal_mod, "draft_exp_in_decomposition", lambda scen, trace: None)

    # Replace DSExperiment in module to our FakeDSExp so isinstance checks work
    monkeypatch.setattr(proposal_mod, "DSExperiment", FakeDSExp, raising=False)

    # Prepare sota experiment with a single model file so Ensemble hypotheses get popped
    sota = FakeDSExp(files={"model1.py": "x"})
    kb = DummyKB()
    trace = DummyTrace(kb, sota)

    scen = DummyScenario()
    inst = make_proposal_instance(scen)

    # Stubs for instance methods to control flow and assert intermediate conditions
    def identify_problem(self, current_sub_trace, scenario_desc, sota_exp_desc, exp_feedback_list_desc, inject_diverse, exp_gen_plan, sibling_exp):
        # return initial problems dict
        return {"prob1": {"desc": "p1"}}

    monkeypatch.setattr(inst, "identify_problem", types.MethodType(identify_problem, inst))

    # hypothesis_gen returns two hypotheses, one Ensemble which should be popped due to model file count <=1
    def hypothesis_gen(self, component_desc, scenario_desc, exp_feedback_list_desc, sota_exp_desc,
                       problems, pipeline, enable_idea_pool, inject_diverse, exp_gen_plan, is_new_tree,
                       sibling_exp, former_user_instructions):
        return {
            "prob1": {"component": "Ensemble", "hypothesis": "ens_hyp"},
            "prob2": {"component": "Simple", "hypothesis": "simple_hyp"},
        }

    monkeypatch.setattr(inst, "hypothesis_gen", types.MethodType(hypothesis_gen, inst))

    # hypothesis_critique should receive hypothesis_dict with 'prob1' popped (because Ensemble removed)
    def hypothesis_critique(self, hypothesis_dict, problems_dict, scenario_desc, sota_exp_desc, exp_feedback_list_desc):
        assert "prob1" not in hypothesis_dict  # ensure Ensemble was popped earlier
        # produce critique for remaining hypothesis
        return {"prob2": {"crit": "ok"}}

    monkeypatch.setattr(inst, "hypothesis_critique", types.MethodType(hypothesis_critique, inst))

    # hypothesis_rewrite returns same dict (simulate improvement)
    def hypothesis_rewrite(self, hypothesis_dict, critiques_dict, scenario_desc, sota_exp_desc, exp_feedback_list_desc, sibling_exp, former_user_instructions):
        # ensure sibling_exp passed through
        assert sibling_exp == ["sib_exp"]
        hypothesis_dict["prob2"]["rewritten"] = True
        return hypothesis_dict

    monkeypatch.setattr(inst, "hypothesis_rewrite", types.MethodType(hypothesis_rewrite, inst))

    # hypothesis_rank picks prob2 and returns a DSHypothesis
    # Use DSHypothesis from module
    DSHypothesis = proposal_mod.DSHypothesis

    def hypothesis_rank(self, hypothesis_dict, problem_dict, selected_idx=None):
        # ensure rewritten flag present
        assert hypothesis_dict["prob2"].get("rewritten", False) is True
        return "prob2", DSHypothesis(component=hypothesis_dict["prob2"]["component"], hypothesis=hypothesis_dict["prob2"]["hypothesis"])

    monkeypatch.setattr(inst, "hypothesis_rank", types.MethodType(hypothesis_rank, inst))

    # get_all_hypotheses returns list; task_gen should be called and return a DSExperiment-like object
    def get_all_hypotheses(self, problem_dict, hypothesis_dict):
        return [DSHypothesis(component="c", hypothesis="h") for _ in hypothesis_dict]

    monkeypatch.setattr(inst, "get_all_hypotheses", types.MethodType(get_all_hypotheses, inst))

    task_result = FakeDSExp(files={"out.txt": "done"})

    def task_gen(self, component_desc, scenario_desc, sota_exp_desc, sota_exp, hypotheses, hypotheses_candidates, pipeline, failed_exp_feedback_list_desc, fb_to_sota_exp, sibling_exp, former_user_instructions):
        # verify a few inputs to ensure flow correctness
        assert isinstance(component_desc, str)
        assert "scenario_desc" in scenario_desc
        # hypotheses should be a list with one DSHypothesis since is_selection_new_tree is False
        assert isinstance(hypotheses, list) and len(hypotheses) == 1
        # hypotheses_candidates should equal to get_all_hypotheses result
        assert isinstance(hypotheses_candidates, list)
        return task_result

    monkeypatch.setattr(inst, "task_gen", types.MethodType(task_gen, inst))

    # Now call gen and assert results and KB interactions
    result = proposal_mod.DSProposalV2ExpGen.gen(inst, trace, plan=None)

    assert result is task_result
    assert kb.sample_called is True  # ensure KB sampling happened
    assert kb.update_called is True  # ensure KB updated with pickled problem
    # last_update_args should have been (all_problems, pickled_problem_name)
    assert isinstance(kb.last_update_args, tuple) and len(kb.last_update_args) == 2
