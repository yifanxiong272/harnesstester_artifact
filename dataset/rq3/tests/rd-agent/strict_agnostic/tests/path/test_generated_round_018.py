import json
import pytest
import importlib


# Tests generated to target KGExperiment2Feedback.generate_feedback branch coverage


def _make_stub_T():
    class StubT:
        def __init__(self, key):
            self.key = key

        def r(self, *args, **kwargs):
            # Return an opaque but deterministic prompt representation
            return f"PROMPT:{self.key}:{sorted(kwargs.keys())}"

    return StubT


class StubAPIBackend:
    def __init__(self, response_dict=None):
        # deterministic response used in tests
        self._response = response_dict or {
            "Observations": "obs",
            "Feedback for Hypothesis": "eval",
            "New Hypothesis": "new",
            "Reasoning": "because",
            "Replace Best Result": "yes",
        }

    def build_messages_and_create_chat_completion(self, *args, **kwargs):
        # return a JSON string as the real function would
        return json.dumps(self._response)


class SimpleNode:
    def __init__(self, content=None, label=None):
        self.content = content
        self.label = label

    def __repr__(self):
        return f"SimpleNode(label={self.label}, content={self.content})"


class KB:
    def __init__(self):
        self.added = []

    def batch_embedding(self, nodes):
        # Return nodes unchanged to preserve object identity checks in the code
        return nodes

    def add_node(self, node, parent):
        # record the add operation for assertions
        self.added.append((node, parent))


def _make_feedback_instance(module):
    # Create instance without calling __init__ to avoid side effects
    inst = object.__new__(module.KGExperiment2Feedback)
    return inst


def test_generate_feedback_no_based_experiments_raises_assertion_round_018(monkeypatch):
    """
    Exercise path where exp.based_experiments is empty (60->66 branch) and ensure the later
    assertion about sota_exp triggers. This verifies the else path where process_results is
    called with current_result compared to itself and that an AssertionError is raised
    when no previous experiments exist.
    """
    feedback_mod = importlib.import_module("rdagent.scenarios.kaggle.developer.feedback")

    # Patch T and APIBackend to deterministic stubs
    monkeypatch.setattr(feedback_mod, "T", _make_stub_T())
    monkeypatch.setattr(feedback_mod, "APIBackend", lambda *args, **kwargs: StubAPIBackend())
    # Ensure convert2bool does not raise and is deterministic
    monkeypatch.setattr(feedback_mod, "convert2bool", lambda v: True if str(v).lower() in ("true", "yes") else False)

    # Prepare instance and scen stub
    inst = _make_feedback_instance(feedback_mod)
    class Scen:
        def get_scenario_all_desc(self, **kwargs):
            return {"desc": "scenario"}
    inst.scen = Scen()

    # Patch process_results on the instance to a deterministic result
    def fake_process_results(curr, sota):
        return ({"combined": 1}, "evaldesc")
    inst.process_results = fake_process_results

    # Build an experiment-like object with empty based_experiments to trigger the else branch
    class Hyp:
        def __init__(self):
            self.hypothesis = "h"
            self.reason = "r"
            self.action = "Some action"

    class Exp:
        def __init__(self):
            self.hypothesis = Hyp()
            self.result = {"score": 0}
            self.based_experiments = []
            self.sub_tasks = []
            self.sub_workspace_list = []
            self.experiment_workspace = type("X", (), {"data_description": "dd", "model_description": {}})()
            self.sub_results = {}

    exp = Exp()

    # trace stub with minimal shape used before assertion
    class Trace:
        def __init__(self):
            self.hist = []
            self.knowledge_base = KB()

    trace = Trace()

    # Because the code later asserts sota_exp is not None, we expect an AssertionError
    with pytest.raises(AssertionError):
        inst.generate_feedback(exp, trace)


def test_generate_feedback_graph_rag_and_ucb_round_018(monkeypatch):
    """
    Exercise path where based_experiments exist, hypothesis.action == "Model tuning",
    scen.if_using_graph_rag == True, and scen.if_action_choosing_based_on_UCB == True.
    This covers creation of nodes, the knowledge base batch_embedding/add_node calls, and
    the UCB action count increment. Also validate returned HypothesisFeedback fields.
    """
    feedback_mod = importlib.import_module("rdagent.scenarios.kaggle.developer.feedback")

    # Patch external helpers with deterministic implementations
    monkeypatch.setattr(feedback_mod, "T", _make_stub_T())
    monkeypatch.setattr(feedback_mod, "APIBackend", lambda *args, **kwargs: StubAPIBackend({
        "Observations": "obs123",
        "Feedback for Hypothesis": "good",
        "New Hypothesis": "try_different",
        "Reasoning": "tested",
        "Replace Best Result": "no",
    }))
    monkeypatch.setattr(feedback_mod, "convert2bool", lambda v: True if str(v).lower() in ("true", "yes") else False)

    # Replace UndirectedNode with our SimpleNode to record content/label
    monkeypatch.setattr(feedback_mod, "UndirectedNode", SimpleNode)

    # Prepare instance
    inst = _make_feedback_instance(feedback_mod)

    # scen stub with flags for graph RAG and UCB
    class Scen:
        def __init__(self):
            self.if_using_vector_rag = False
            self.if_using_graph_rag = True
            self.if_action_choosing_based_on_UCB = True
            self.action_counts = {"Model tuning": 0}

        def get_scenario_all_desc(self, **kwargs):
            return {"desc": "scenario"}

        def get_competition_full_desc(self):
            return "competition description"

    sc = Scen()
    inst.scen = sc

    # Patch process_results to return deterministic combined_result and description
    def fake_process_results(curr, sota):
        return ({"acc": 0.9}, "evaldesc")
    inst.process_results = fake_process_results

    # Build experiment with based_experiments non-empty and necessary attributes
    class Hyp:
        def __init__(self):
            self.hypothesis = "improve model"
            self.reason = "tune hyperparams"
            self.action = "Model tuning"

    class BasedExpWorkspace:
        def __init__(self):
            self.data_description = "features x,y"
            self.model_description = {"model": "xgboost"}

    class BasedExp:
        def __init__(self):
            self.result = {"score": 0.8}
            self.sub_results = {"s": 1}
            self.experiment_workspace = BasedExpWorkspace()

    class SubTask:
        def get_task_information(self):
            return "task-info"

    class SubWS:
        def __init__(self):
            self.all_codes = "print('hello')"

    class Exp:
        def __init__(self):
            self.hypothesis = Hyp()
            self.result = {"score": 0.85}
            self.based_experiments = [BasedExp()]
            self.sub_tasks = [SubTask()]
            self.sub_workspace_list = [SubWS()]
            self.experiment_workspace = type("X", (), {"file_dict": {}})()
            self.sub_results = {"a": 1}

    exp = Exp()

    # trace and knowledge base
    kb = KB()
    class Trace:
        def __init__(self):
            self.hist = [(Hyp(), "old feedback")]
            self.knowledge_base = kb

    trace = Trace()

    # Call the function under test
    result = inst.generate_feedback(exp, trace)

    # Validate the returned feedback fields (oracle)
    assert getattr(result, "observations") == "obs123"
    assert getattr(result, "hypothesis_evaluation") == "good"
    assert getattr(result, "new_hypothesis") == "try_different"
    assert getattr(result, "reason") == "tested"
    # 'Replace Best Result' was "no" -> convert2bool -> False
    assert getattr(result, "decision") is False

    # Ensure knowledge base add_node was called for nodes other than competition
    # We expect at least hypothesis_node, a code node, and conclusion node to be added
    # competition node should not have been added to 'added'
    assert len(kb.added) >= 3
    # Ensure UCB action count has been incremented
    assert sc.action_counts["Model tuning"] == 1
