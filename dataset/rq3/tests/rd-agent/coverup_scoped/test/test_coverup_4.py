# file: rdagent/scenarios/kaggle/developer/feedback.py:40-191
# asked: {"lines": [45, 54, 55, 56, 58, 60, 61, 63, 66, 67, 69, 72, 73, 74, 75, 77, 80, 81, 84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95, 96, 97, 98, 99, 102, 103, 105, 106, 107, 109, 110, 111, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 130, 132, 133, 134, 135, 136, 139, 141, 142, 143, 144, 145, 157, 158, 159, 160, 163, 164, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 182, 183, 185, 186, 187, 188, 189, 190], "branches": [[60, 61], [60, 66], [72, 73], [72, 74], [74, 75], [74, 77], [95, 96], [95, 97], [97, 98], [97, 102], [110, 111], [110, 114], [163, 164], [163, 167], [167, 168], [167, 182], [171, 172], [171, 175], [173, 171], [173, 174], [178, 179], [178, 182], [179, 178], [179, 180], [182, 183], [182, 185]]}
# gained: {"lines": [45, 54, 55, 56, 58, 60, 61, 63, 72, 73, 74, 77, 80, 81, 84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95, 96, 97, 102, 103, 105, 106, 107, 109, 110, 111, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 130, 132, 133, 134, 135, 136, 139, 141, 142, 143, 144, 145, 157, 158, 159, 160, 163, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 182, 183, 185, 186, 187, 188, 189, 190], "branches": [[60, 61], [72, 73], [72, 74], [74, 77], [95, 96], [95, 97], [97, 102], [110, 111], [110, 114], [163, 167], [167, 168], [167, 182], [171, 172], [171, 175], [173, 174], [178, 179], [178, 182], [179, 178], [179, 180], [182, 183], [182, 185]]}

import json
import types
import pytest
import importlib


@pytest.fixture(autouse=True)
def ensure_clean_imports():
    # Ensure fresh import of module to allow monkeypatching without cross-test pollution
    importlib.reload(importlib.import_module("rdagent.scenarios.kaggle.developer.feedback"))
    yield
    # reload after test to revert any module-level monkeypatch effects
    importlib.reload(importlib.import_module("rdagent.scenarios.kaggle.developer.feedback"))


def make_fake_scene(if_using_graph_rag=True, if_using_vector_rag=False, if_action_choosing_based_on_UCB=False):
    class FakeScene:
        def __init__(self):
            self.if_using_graph_rag = if_using_graph_rag
            self.if_using_vector_rag = if_using_vector_rag
            self.if_action_choosing_based_on_UCB = if_action_choosing_based_on_UCB
            # action_counts is expected to be a dict indexed by hypothesis.action strings
            self.action_counts = {}
            # placeholders
            self.vector_base = types.SimpleNamespace(add_experience_to_vector_base=lambda x: None, dump=lambda: None)

        def get_scenario_all_desc(self, filtered_tag=None):
            return "scenario_all_desc"

        def get_competition_full_desc(self):
            return "competition_full_desc"

    return FakeScene()


def setup_common_monkeypatches(monkeypatch, fb_mod, api_response: dict):
    # Monkeypatch T so templating returns predictable prompts
    class FakeTpl:
        def __init__(self, key):
            self.key = key

        def r(self, *args, **kwargs):
            # return a stable string
            return f"rendered:{self.key}:{args}:{kwargs}"

    monkeypatch.setattr(fb_mod, "T", FakeTpl)

    # Monkeypatch APIBackend to return our provided JSON
    class FakeAPIBackend:
        def build_messages_and_create_chat_completion(self, *, user_prompt, system_prompt, json_mode, json_target_type):
            # Just return JSON string
            return json.dumps(api_response)

    monkeypatch.setattr(fb_mod, "APIBackend", FakeAPIBackend)

    # Replace UndirectedNode with simple class to avoid heavy graph deps
    class SimpleNode:
        def __init__(self, content=None, label=None):
            self.content = content
            self.label = label

        def __repr__(self):
            return f"SimpleNode({self.label}:{self.content})"

    monkeypatch.setattr(fb_mod, "UndirectedNode", SimpleNode)


def make_based_experiment():
    # Create a fake based experiment object used by exp.based_experiments
    class BasedExp:
        def __init__(self):
            self.result = {"score": 0.8}
            self.sub_results = {"sub": 0.5}
            self.experiment_workspace = types.SimpleNamespace(
                data_description="sota_features_desc",
                model_description={"model": "desc"},
                file_dict={"dummy": "value"},
            )

    return BasedExp()


def make_trace_with_kb(hist=None):
    # Fake knowledge base
    class FakeKB:
        def __init__(self):
            self.added = []

        def batch_embedding(self, nodes):
            # pretend embedding by returning same nodes
            return nodes

        def add_node(self, node, competition_node):
            # record added node relationships
            self.added.append((node, competition_node))

    class FakeTrace:
        def __init__(self, kb, hist):
            self.scen = None
            self.hist = hist or []
            self.knowledge_base = kb

    kb = FakeKB()
    return FakeTrace(kb, hist), kb


def make_experiment(action, model_type_for_select=None, num_subtasks=1):
    # Build a minimal experiment-like object satisfying attributes accessed in method
    class Task:
        def __init__(self, model_type=None, info="task_info"):
            self.model_type = model_type
            self._info = info

        def get_task_information(self):
            return self._info

    class SubWS:
        def __init__(self, target_task=None, all_codes="print('hello')"):
            self.target_task = target_task
            self.all_codes = all_codes

    class Exp:
        def __init__(self):
            self.hypothesis = types.SimpleNamespace(hypothesis="h_text", reason="h_reason", action=action)
            self.sub_tasks = [Task(model_type=model_type_for_select) for _ in range(num_subtasks)]
            # placeholder: will be set by tests as needed
            self.sub_workspace_list = []
            self.based_experiments = []
            self.experiment_workspace = types.SimpleNamespace(file_dict={})
            self.result = {"score": 0.9}
            self.sub_results = {"s1": 0.1}

    exp = Exp()
    # create sub_workspace_list entries
    exp.sub_workspace_list = [SubWS(target_task=exp.sub_tasks[i], all_codes=f"code_{i}") for i in range(num_subtasks)]
    return exp


def test_generate_feedback_model_tuning_graph_rag_ucb(monkeypatch):
    fb_mod = importlib.import_module("rdagent.scenarios.kaggle.developer.feedback")
    # API will provide expected keys
    api_response = {
        "Observations": "obs text",
        "Feedback for Hypothesis": "eval text",
        "New Hypothesis": "new hyp",
        "Reasoning": "because",
        "Replace Best Result": "yes",
    }
    setup_common_monkeypatches(monkeypatch, fb_mod, api_response)

    # Prepare scene and instance
    scen = make_fake_scene(if_using_graph_rag=True, if_using_vector_rag=False, if_action_choosing_based_on_UCB=True)
    # Ensure action_counts contains the relevant key
    scen.action_counts["Model tuning"] = 0

    # instantiate KGExperiment2Feedback with scen
    KGCls = fb_mod.KGExperiment2Feedback
    instance = KGCls(scen)

    # Make exp with Model tuning (action triggers sub_workspace_list[0].all_codes usage)
    exp = make_experiment("Model tuning", model_type_for_select=None, num_subtasks=1)
    # Provide based_experiments so sota_exp is populated
    based = make_based_experiment()
    exp.based_experiments = [based]
    # Provide experiment_workspace for exp itself
    exp.experiment_workspace = types.SimpleNamespace(file_dict={"dummy": "val"}, data_description="cur_features", model_description={"m": "d"})
    # override process_results to a deterministic return (set on instance)
    def fake_process_results(cur, sota):
        return ({"metric": 0.95}, "evaluation_description")
    monkeypatch.setattr(instance, "process_results", fake_process_results, raising=False)

    # Prepare trace with one previous history entry to exercise last_hypothesis_and_feedback branch
    last_hyp = types.SimpleNamespace(hypothesis="prev_hyp")
    trace, kb = make_trace_with_kb(hist=[(last_hyp, "prev_feedback")])

    # attach trace.scen (not strictly required) and ensure knowledge base methods exist
    trace.scen = scen

    # Call generate_feedback
    feedback = instance.generate_feedback(exp, trace)

    # Assertions: output should match API response and converted decision True
    assert isinstance(feedback, fb_mod.HypothesisFeedback)
    assert feedback.observations == "obs text"
    assert feedback.hypothesis_evaluation == "eval text"
    assert feedback.new_hypothesis == "new hyp"
    assert feedback.reason == "because"
    # Decision originally passed as "yes" -> convert2bool should produce True
    assert feedback.decision is True

    # Graph RAG: nodes (excluding competition node) should have been added to kb.added
    # There should be at least one added node (hypothesis node, codes, conclusion)
    assert len(kb.added) >= 1
    # action_counts should have been incremented
    assert scen.action_counts["Model tuning"] == 1


def test_generate_feedback_other_action_builds_subexp_codes(monkeypatch):
    fb_mod = importlib.import_module("rdagent.scenarios.kaggle.developer.feedback")
    # Response with no/other fields to ensure defaults are handled
    api_response = {
        "Observations": "obs2",
        "Feedback for Hypothesis": "eval2",
        "New Hypothesis": "new2",
        "Reasoning": "r2",
        "Replace Best Result": "no",
    }
    setup_common_monkeypatches(monkeypatch, fb_mod, api_response)

    scen = make_fake_scene(if_using_graph_rag=False, if_using_vector_rag=False, if_action_choosing_based_on_UCB=False)
    KGCls = fb_mod.KGExperiment2Feedback
    instance = KGCls(scen)

    # Create experiment with an "Other" action to hit the else branch building current_sub_exps_to_code from sub_workspace_list
    exp = make_experiment("Some other action", num_subtasks=2)
    # Provide based_experiments so sota_exp is populated
    based = make_based_experiment()
    exp.based_experiments = [based]
    exp.experiment_workspace = types.SimpleNamespace(file_dict={"k": "v"}, data_description="cur_features", model_description={"m": "d"})
    # process_results deterministic (set on instance)
    def fake_process_results(cur, sota):
        return ({"metric": 0.5}, "eval desc")
    monkeypatch.setattr(instance, "process_results", fake_process_results, raising=False)

    # trace with empty history to test last_hypothesis_and_feedback None branch
    trace, kb = make_trace_with_kb(hist=[])
    trace.scen = scen

    feedback = instance.generate_feedback(exp, trace)

    assert isinstance(feedback, fb_mod.HypothesisFeedback)
    assert feedback.observations == "obs2"
    assert feedback.hypothesis_evaluation == "eval2"
    assert feedback.new_hypothesis == "new2"
    assert feedback.reason == "r2"
    # Replace Best Result was "no" -> decision False
    assert feedback.decision is False
    # Since graph_rag and vector_rag are False, knowledge base should not have new nodes added
    assert len(kb.added) == 0
