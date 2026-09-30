import json
import types

import pytest

from rdagent.scenarios.kaggle.developer import feedback as fb_mod
from rdagent.core.proposal import HypothesisFeedback


# Helpers used to patch module-level collaborators deterministically
class FakeRenderer:
    def __init__(self, key):
        self.key = key

    def r(self, *args, **kwargs):
        # Return a stable string containing the key and a sorted representation of kwargs
        if kwargs:
            items = ",".join(f"{k}={repr(kwargs[k])}" for k in sorted(kwargs))
            return f"RENDER[{self.key}]({items})"
        return f"RENDER[{self.key}](args={args})"


class FakeAPIBackend:
    def __init__(self, response_str):
        self._response = response_str

    def build_messages_and_create_chat_completion(self, **kwargs):
        # ignore kwargs, return the preconfigured JSON string
        return self._response


class FakeNode:
    def __init__(self, content=None, label=None):
        self.content = content
        self.label = label

    def __repr__(self):
        return f"FakeNode(label={self.label!r}, content={self.content!r})"


class FakeKB:
    def __init__(self):
        self.added = []

    def batch_embedding(self, nodes):
        # deterministic: return the same list object so identity of competition_node is preserved
        return nodes

    def add_node(self, node, competition_node):
        # record the tuple for assertions
        self.added.append((node, competition_node))


class DummyScenario:
    def __init__(self):
        self._desc = "scenario-all-desc"
        self.if_using_vector_rag = False
        self.if_using_graph_rag = False
        self.if_action_choosing_based_on_UCB = False
        self.vector_base = types.SimpleNamespace(add_experience_to_vector_base=lambda *_: None, dump=lambda: None)
        self.action_counts = {}

    def get_scenario_all_desc(self, filtered_tag=None):
        return f"SCEN_DESC({filtered_tag})"

    def get_competition_full_desc(self):
        return "COMPETITION_FULL_DESC"


# Minimal dummy experiment/hypothesis/substructures with only attributes accessed by the code
class DummyHypothesis:
    def __init__(self, hypothesis, reason, action):
        self.hypothesis = hypothesis
        self.reason = reason
        self.action = action


class DummyTask:
    def __init__(self, info, model_type=None):
        self._info = info
        self.model_type = model_type

    def get_task_information(self):
        return self._info


class DummyWorkspace:
    def __init__(self, data_description=None, model_description=None, file_dict=None, all_codes=None, target_task=None):
        self.data_description = data_description
        self.model_description = model_description
        self.file_dict = file_dict or {}
        self.all_codes = all_codes
        self.target_task = target_task


class DummyExperiment:
    def __init__(self):
        self.hypothesis = None
        self.result = {"score": 0}
        self.based_experiments = []
        self.sub_tasks = []
        self.sub_workspace_list = []
        self.sub_results = []
        self.experiment_workspace = DummyWorkspace()


class DummyTrace:
    def __init__(self, hist=None, kb=None):
        self.hist = hist or []
        self.knowledge_base = kb or FakeKB()


# Patch module-level functions and constants inside the feedback module for deterministic tests
@pytest.fixture(autouse=True)
def patch_feedback_module(monkeypatch):
    # T renderer
    monkeypatch.setattr(fb_mod, "T", lambda key: FakeRenderer(key))
    # convert2bool simple deterministic mapping
    monkeypatch.setattr(fb_mod, "convert2bool", lambda v: True if str(v).lower() in ("yes", "true", "1") else False)
    # Provide a minimal KG_SELECT_MAPPING used by feature selection branch
    monkeypatch.setattr(fb_mod, "KG_SELECT_MAPPING", {"dt": "select_dt", "rf": "select_rf"})
    # Provide a simple UndirectedNode implementation that matches attribute access used in the code
    monkeypatch.setattr(fb_mod, "UndirectedNode", FakeNode)
    yield


def make_feedback_instance():
    # Create instance without invoking real constructor requirements
    inst = object.__new__(fb_mod.KGExperiment2Feedback)
    inst.scen = DummyScenario()
    # bind a simple deterministic process_results to the instance
    def _process_results(self, current_result, sota_result):
        # return a combined_result and a textual description
        combined = {"combined_score": (current_result.get("score", 0) + sota_result.get("score", 0))}
        return combined, "evaluation-desc"

    # Attach as bound method
    inst.process_results = types.MethodType(_process_results, inst)
    return inst


def test_generate_feedback_feature_selection_no_based_exp_round_018(monkeypatch):
    """
    Scenario tested:
    - exp.based_experiments is empty (branch: compare with itself)
    - hypothesis.action == "Model feature selection" (branch for prompt_key and building current_sub_exps_to_code via KG_SELECT_MAPPING)
    - scen.if_using_graph_rag and scen.if_using_vector_rag are False
    - scen.if_action_choosing_based_on_UCB is True (action_counts incremented)
    Assertions:
    - returned HypothesisFeedback fields reflect the fake API response
    - scen.action_counts for the hypothesis.action increments
    """
    inst = make_feedback_instance()

    # Prepare the experiment with no based_experiments
    exp = DummyExperiment()
    exp.hypothesis = DummyHypothesis(hypothesis="HYP_TEXT", reason="some reason", action="Model feature selection")
    exp.result = {"score": 10}

    # Subtask and experiment workspace so that file_dict[KG_SELECT_MAPPING[model_type]] is accessible
    subtask = DummyTask(info="task-A", model_type="dt")
    exp.sub_tasks = [subtask]
    exp.experiment_workspace = DummyWorkspace(file_dict={"select_dt": "selected-code-snippet"})

    # Configure scenario to increment action counts
    inst.scen.if_using_vector_rag = False
    inst.scen.if_using_graph_rag = False
    inst.scen.if_action_choosing_based_on_UCB = True
    inst.scen.action_counts = {"Model feature selection": 0}

    # Provide deterministic API response
    response_obj = {
        "Observations": "obs-1",
        "Feedback for Hypothesis": "eval-1",
        "New Hypothesis": "new-1",
        "Reasoning": "reason-1",
        "Replace Best Result": "yes"
    }
    monkeypatch.setattr(fb_mod, "APIBackend", lambda: FakeAPIBackend(json.dumps(response_obj)))

    # Call the method
    trace = DummyTrace()
    out = inst.generate_feedback(exp, trace)

    # Validate the type and content of returned HypothesisFeedback
    assert isinstance(out, HypothesisFeedback)
    assert out.observations == "obs-1"
    assert out.hypothesis_evaluation == "eval-1"
    assert out.new_hypothesis == "new-1"
    assert out.reason == "reason-1"
    # convert2bool maps "yes"->True
    assert out.decision is True

    # action_counts should have incremented
    assert inst.scen.action_counts["Model feature selection"] == 1


def test_generate_feedback_with_based_experiment_graph_rag_round_018(monkeypatch):
    """
    Scenario tested:
    - exp.based_experiments is present (branch selecting sota_result and sota_* values)
    - hypothesis.action == "Model tuning" (branch which uses sub_workspace_list[0].all_codes)
    - scen.if_using_graph_rag True (graph RAG branch), ensure knowledge_base.batch_embedding and add_node are invoked deterministically
    - trace.hist contains prior hypothesis to populate last_hypothesis_and_feedback
    Assertions:
    - returned HypothesisFeedback contains fields from the fake API response
    - knowledge_base.add_node recorded expected pairs (nodes not being the same identity as competition_node are added)
    """
    inst = make_feedback_instance()

    # Build experiment with a based_experiment for sota
    exp = DummyExperiment()
    exp.hypothesis = DummyHypothesis(hypothesis="HTUNE", reason="reason-tune", action="Model tuning")
    exp.result = {"score": 5}

    # Based experiment stub with expected attributes used by the code
    based = types.SimpleNamespace(
        result={"score": 7},
        experiment_workspace=types.SimpleNamespace(
            data_description="DATA_DESC",
            model_description={"m": "desc"}
        ),
        sub_results=[{"sub": 1}],
        experiment_workspace_model=None
    )
    # attach experiment_workspace.model_description properly (the attribute used by code is model_description)
    based.experiment_workspace.model_description = {"m": "desc"}
    exp.based_experiments = [based]

    # For model tuning branch: sub_tasks and sub_workspace_list
    subtask = DummyTask(info="task-tune", model_type="rf")
    subws = DummyWorkspace(all_codes="print(\"code-tune\")")
    exp.sub_tasks = [subtask]
    exp.sub_workspace_list = [subws]

    # Scenario configuration to enable graph RAG
    inst.scen.if_using_graph_rag = True
    inst.scen.if_using_vector_rag = False
    inst.scen.if_action_choosing_based_on_UCB = False

    # Prepare a trace with knowledge base that records add_node calls
    kb = FakeKB()
    trace = DummyTrace(hist=[(DummyHypothesis(hypothesis="OLD_H", reason="r", action="act"), "old-feedback")], kb=kb)

    # Prepare API response where Replace Best Result is "no"
    response_obj = {
        "Observations": "obs-graph",
        "Feedback for Hypothesis": "eval-graph",
        "New Hypothesis": "new-graph",
        "Reasoning": "reason-graph",
        "Replace Best Result": "no"
    }
    monkeypatch.setattr(fb_mod, "APIBackend", lambda: FakeAPIBackend(json.dumps(response_obj)))

    # Call the method
    out = inst.generate_feedback(exp, trace)

    # Validate returned content
    assert isinstance(out, HypothesisFeedback)
    assert out.observations == "obs-graph"
    assert out.hypothesis_evaluation == "eval-graph"
    assert out.new_hypothesis == "new-graph"
    assert out.reason == "reason-graph"
    assert out.decision is False

    # In graph RAG, the knowledge_base.add_node should be called for nodes not identical to competition_node
    # The implementation in generate_feedback constructs: [competition_node, hypothesis_node, *exp_code_nodes, conclusion_node]
    # and batch_embedding returns the same list; therefore add_node should be called for nodes other than the first one
    assert len(kb.added) >= 1
    # Confirm the second entry in added references a node and the competition node
    node, comp = kb.added[0]
    assert isinstance(node, FakeNode) and isinstance(comp, FakeNode)
    assert comp.label == "competition"


def test_generate_feedback_vector_rag_raises_round_018(monkeypatch):
    """
    Scenario tested:
    - scen.if_using_vector_rag True triggers the NotImplementedError branch
    Assertion: NotImplementedError is raised deterministically
    """
    inst = make_feedback_instance()

    exp = DummyExperiment()
    exp.hypothesis = DummyHypothesis(hypothesis="H", reason="r", action="factor")
    exp.result = {"score": 1}

    # No based_experiments (so the code will compare with itself first)
    inst.scen.if_using_vector_rag = True

    # Minimal response even though it should not reach API call in this branch
    monkeypatch.setattr(fb_mod, "APIBackend", lambda: FakeAPIBackend(json.dumps({})))

    with pytest.raises(NotImplementedError):
        inst.generate_feedback(exp, DummyTrace())
