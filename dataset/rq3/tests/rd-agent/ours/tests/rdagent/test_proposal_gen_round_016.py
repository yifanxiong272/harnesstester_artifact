import importlib
import types
import pytest

MODULE_PATH = "rdagent.scenarios.data_science.proposal.exp_gen.proposal"

@pytest.fixture(autouse=True)
def reload_module():
    # Ensure a fresh import so we can patch module-level symbols deterministically
    if MODULE_PATH in globals():
        del globals()[MODULE_PATH]
    mod = importlib.import_module(MODULE_PATH)
    yield mod

class DummyKB:
    def __init__(self):
        self.sample_called = False
        self.updated = False
    def sample_ideas(self, problems, **kwargs):
        # deterministic augmentation to show it was used
        self.sample_called = True
        problems.append("kb_added_problem")
        return problems
    def update_pickled_problem(self, all_problems, pickled_problem_name):
        self.updated = True

class DummyExperiment:
    def __init__(self, file_dict=None):
        self.experiment_workspace = types.SimpleNamespace(file_dict=(file_dict or {}))

class DummyTrace:
    def __init__(self, *, sota_fb=None, hist=None, current_selection=None, failed_list=None):
        self._sota_fb = sota_fb
        self.hist = hist if hist is not None else []
        self.current_selection = current_selection if current_selection is not None else []
        self._failed_list = failed_list if failed_list is not None else []
        self.knowledge_base = DummyKB()
        self._is_new_tree = False
        self._should_inject = True
        self._sibling_exps = ["sib"]
    def sota_experiment_fb(self):
        return self._sota_fb
    def experiment_and_feedback_list_after_init(self, return_type="all"):
        if return_type == "all":
            # return a deterministic list of tuples (exp, fb)
            return [(DummyExperiment({}), "fb1")]
        if return_type == "failed":
            return self._failed_list
        return []
    def is_selection_new_tree(self):
        return self._is_new_tree
    def should_inject_diversity(self):
        return self._should_inject
    def get_sibling_exps(self):
        return self._sibling_exps
    def get_parent_exps(self):
        return ["parent1"]


def make_dummy_scen():
    # Minimal scenario object satisfying methods used by DSProposalV2ExpGen
    return types.SimpleNamespace(
        get_scenario_all_desc=lambda eda_output=None: "scenario_desc",
        get_competition_full_desc=lambda: "competition",
    )

def test_gen_returns_draft_when_draft_present_round_016(reload_module):
    mod = reload_module
    # Arrange: Make pipeline disabled and draft_exp_in_decomposition return a DummyExperiment
    mod.DS_RD_SETTING.coder_on_whole_pipeline = False
    draft = DummyExperiment({})
    # Patch draft_exp_in_decomposition to return a draft
    mod.draft_exp_in_decomposition = lambda scen, trace: draft

    trace = DummyTrace()
    dummy_scen = make_dummy_scen()
    gen = mod.DSProposalV2ExpGen(dummy_scen)

    # Act
    result = gen.gen(trace=trace, plan=None)

    # Assert: early return returns the draft object exactly
    assert result is draft


def test_gen_pipeline_true_and_knowledge_base_round_016(reload_module):
    mod = reload_module
    # Set pipeline True path
    mod.DS_RD_SETTING.coder_on_whole_pipeline = True
    # enable knowledge base so sample_ideas is used
    mod.DS_RD_SETTING.enable_knowledge_base = True
    # enable hypo critique/rewrite and llm selection to hit those branches
    mod.DS_RD_SETTING.enable_hypo_critique_rewrite = True
    mod.DS_RD_SETTING.llm_select_hypothesis = True
    mod.DS_RD_SETTING.enable_inject_diverse = False

    # Patch T to provide .r() for pipeline case
    class DummyT:
        def __init__(self, *a, **k):
            pass
        def r(self, *a, **k):
            return "COMPONENT_DESC_FROM_T"
        @property
        def template(self):
            return {"k1": "v1"}
    mod.T = lambda *a, **k: DummyT()

    # Create a sota experiment (will be recognized as DSExperiment by isinstance)
    sota = DummyExperiment({"EDA.md": "eda content", "model_a.py": "x", "model_b.py": "y"})
    # Patch DSExperiment class in module to match isinstance check
    mod.DSExperiment = DummyExperiment

    trace = DummyTrace(sota_fb=(sota, "fbref"), hist=[1], current_selection=["sel"])

    # Patch identify_problem to return a deterministic problems list and record injected arg
    captured = {}
    def identify_problem_inner(**kwargs):
        captured['inject_diverse'] = kwargs.get('inject_diverse')
        return ["p1"]
    mod.DSProposalV2ExpGen.identify_problem = lambda self, **kw: identify_problem_inner(**kw)

    # Patch hypothesis_gen to return deterministic hypothesis dict
    hypo_dict = {
        "probA": {"component": "Model", "hypothesis": "hA"},
    }
    mod.DSProposalV2ExpGen.hypothesis_gen = lambda self, **kw: dict(hypo_dict)

    # Patch hypothesis_critique and hypothesis_rewrite to simulate transform
    def critique(self, **kw):
        return {"probA": "critiqueA"}
    def rewrite(self, hypothesis_dict, **kw):
        # produce a rewritten hypothesis dict
        new = {k: {**v, "rewritten": True} for k, v in hypothesis_dict.items()}
        return new
    mod.DSProposalV2ExpGen.hypothesis_critique = critique
    mod.DSProposalV2ExpGen.hypothesis_rewrite = rewrite

    # Patch hypothesis_select_with_llm to return mapping used to construct DSHypothesis
    mod.DSProposalV2ExpGen.hypothesis_select_with_llm = lambda self, **kw: {"component": "ModelComp", "hypothesis": "sel_hypo"}

    # Capture calls to task_gen
    called = {}
    def fake_task_gen(self, **kw):
        called.update(kw)
        return {"marker": True, "received_component_desc": kw.get('component_desc'), 'hypotheses': kw.get('hypotheses')}
    mod.DSProposalV2ExpGen.task_gen = fake_task_gen

    # Act
    dummy_scen = make_dummy_scen()
    gen = mod.DSProposalV2ExpGen(dummy_scen)
    result = gen.gen(trace=trace, plan=None)

    # Assert: component_desc came from T.r(), knowledge base sample used, critique and rewrite used, and result from task_gen returned
    assert result["marker"] is True
    assert result["received_component_desc"] == "COMPONENT_DESC_FROM_T"
    assert trace.knowledge_base.sample_called is True
    # ensure rewrite flag passed through into constructed hypothesis used by task_gen (via hypotheses arg)
    hypotheses = called.get('hypotheses')
    # When llm_select_hypothesis True, hypotheses should be a list with a DSHypothesis instance
    assert isinstance(hypotheses, list)
    new_hypo = hypotheses[0]
    assert getattr(new_hypo, 'component', None) == 'ModelComp'
    assert getattr(new_hypo, 'hypothesis', None) == 'sel_hypo'
    # knowledge base update should be attempted (enable_knowledge_base True path at end)
    assert trace.knowledge_base.updated is True


def test_gen_non_pipeline_pop_ensemble_round_016(reload_module):
    mod = reload_module
    # Set pipeline False path
    mod.DS_RD_SETTING.coder_on_whole_pipeline = False
    mod.DS_RD_SETTING.enable_knowledge_base = False
    # enable inject diverse so branch is exercised
    mod.DS_RD_SETTING.enable_inject_diverse = True
    mod.DS_RD_SETTING.enable_hypo_critique_rewrite = False
    mod.DS_RD_SETTING.llm_select_hypothesis = False

    # Patch T so template is used in non-pipeline branch
    class DummyT2:
        def __init__(self, *a, **k):
            pass
        def r(self, *a, **k):
            return "unused"
        @property
        def template(self):
            return {"A": "descA", "B": "descB"}
    mod.T = lambda *a, **k: DummyT2()

    # ensure draft_exp_in_decomposition returns None so we proceed
    mod.draft_exp_in_decomposition = lambda scen, trace: None

    # Create sota experiment with only 1 model file so model file count <=1 triggers Ensemble pop
    sota = DummyExperiment({"model_x.py": "m"})
    mod.DSExperiment = DummyExperiment

    # Create a trace with hist non-empty and current_selection empty so inject_diverse True
    trace = DummyTrace(sota_fb=(sota, None), hist=[1], current_selection=[])

    # Patch identify_problem to capture inject_diverse argument (must accept self)
    cap = {}
    def identify_problem(self, current_sub_trace, scenario_desc, sota_exp_desc, exp_feedback_list_desc, inject_diverse, **kw):
        cap['inject_diverse'] = inject_diverse
        return ["p1"]
    mod.DSProposalV2ExpGen.identify_problem = identify_problem

    # Build a hypothesis_dict with an Ensemble component so it should be popped when model file count <=1
    hypo_dict = {
        "hp1": {"component": "Ensemble", "hypothesis": "ensem_h"},
        "hp2": {"component": "Model", "hypothesis": "m_h"},
    }
    mod.DSProposalV2ExpGen.hypothesis_gen = lambda self, **kw: dict(hypo_dict)

    # Patch hypothesis_rank to simply return deterministic selection and capture hypothesis_dict passed in
    captured = {}
    def hypothesis_rank(self, hypothesis_dict, problem_dict):
        captured['hypo_keys'] = list(hypothesis_dict.keys())
        return ("picked", types.SimpleNamespace(component="c", hypothesis="h"))
    mod.DSProposalV2ExpGen.hypothesis_rank = hypothesis_rank

    # Patch task_gen to return the hypotheses candidates so we can assert popped name
    def fake_task_gen(self, **kw):
        return {'hypotheses_candidates': kw.get('hypotheses_candidates'), 'inject_diverse_received': kw.get('inject_diverse', None)}
    mod.DSProposalV2ExpGen.task_gen = fake_task_gen

    dummy_scen = make_dummy_scen()
    gen = mod.DSProposalV2ExpGen(dummy_scen)
    result = gen.gen(trace=trace, plan=None)

    # Assert identify_problem received inject_diverse True
    assert cap.get('inject_diverse') is True
    # Assert Ensemble was popped from hypothesis_dict before hypothesis_rank was called
    assert 'hp1' not in captured.get('hypo_keys', [])
    # ensure task_gen got hypotheses_candidates present in result
    assert 'hypotheses_candidates' in result
