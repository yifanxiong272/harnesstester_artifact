# file: rdagent/scenarios/kaggle/developer/feedback.py:40-191
# asked: {"lines": [45, 54, 55, 56, 58, 60, 61, 63, 66, 67, 69, 72, 73, 74, 75, 77, 80, 81, 84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95, 96, 97, 98, 99, 102, 103, 105, 106, 107, 109, 110, 111, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 130, 132, 133, 134, 135, 136, 139, 141, 142, 143, 144, 145, 157, 158, 159, 160, 163, 164, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 182, 183, 185, 186, 187, 188, 189, 190], "branches": [[60, 61], [60, 66], [72, 73], [72, 74], [74, 75], [74, 77], [95, 96], [95, 97], [97, 98], [97, 102], [110, 111], [110, 114], [163, 164], [163, 167], [167, 168], [167, 182], [171, 172], [171, 175], [173, 171], [173, 174], [178, 179], [178, 182], [179, 178], [179, 180], [182, 183], [182, 185]]}
# gained: {"lines": [45, 54, 55, 56, 58, 60, 61, 63, 72, 73, 74, 77, 80, 81, 84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95, 96, 97, 102, 103, 105, 106, 107, 109, 110, 111, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 130, 132, 133, 134, 135, 136, 139, 141, 142, 143, 144, 145, 157, 158, 159, 160, 163, 164, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 182, 183, 185, 186, 187, 188, 189, 190], "branches": [[60, 61], [72, 73], [72, 74], [74, 77], [95, 96], [95, 97], [97, 102], [110, 111], [110, 114], [163, 164], [163, 167], [167, 168], [171, 172], [171, 175], [173, 174], [178, 179], [178, 182], [179, 178], [179, 180], [182, 183]]}

import json
import types
import pytest

from rdagent.scenarios.kaggle.developer import feedback as feedback_module
from rdagent.scenarios.kaggle.developer.feedback import KGExperiment2Feedback


class DummyTObj:
    def __init__(self, return_value):
        self._return_value = return_value

    def r(self, *args, **kwargs):
        return self._return_value


class DummyTFactory:
    def __call__(self, key):
        if ".system" in key:
            return DummyTObj("SYSTEM_PROMPT")
        return DummyTObj("USER_PROMPT")


class FakeAPIBackend:
    def __init__(self, response_obj):
        self._response_obj = response_obj

    def build_messages_and_create_chat_completion(self, *args, **kwargs):
        return json.dumps(self._response_obj)


class DummyKB:
    def __init__(self):
        self.added = []

    def batch_embedding(self, nodes):
        return nodes

    def add_node(self, node, parent):
        self.added.append((node, parent))


class SimpleTask:
    def __init__(self, info):
        self._info = info

    def get_task_information(self):
        return self._info


class SimpleSubWS:
    def __init__(self, target_info, all_codes):
        self.target_task = SimpleTask(target_info)
        self.all_codes = all_codes


class SimpleExperimentWS:
    def __init__(self, data_description, model_description, file_dict=None):
        self.data_description = data_description
        self.model_description = model_description
        self.file_dict = file_dict or {}


class SimpleBasedExperiment:
    def __init__(self, experiment_workspace, result, sub_results):
        self.experiment_workspace = experiment_workspace
        self.result = result
        self.sub_results = sub_results


class SimpleHypothesis:
    def __init__(self, hypothesis_text, reason_text, action_text):
        self.hypothesis = hypothesis_text
        self.reason = reason_text
        self.action = action_text


class SimpleTrace:
    def __init__(self, kb, hist=None):
        self.knowledge_base = kb
        self.hist = hist or []


class SimpleScen:
    def __init__(
        self,
        evaluation_metric_direction=True,
        if_using_vector_rag=False,
        if_using_graph_rag=True,
        if_action_choosing_based_on_UCB=True,
    ):
        self.evaluation_metric_direction = evaluation_metric_direction
        self.if_using_vector_rag = if_using_vector_rag
        self.if_using_graph_rag = if_using_graph_rag
        self.if_action_choosing_based_on_UCB = if_action_choosing_based_on_UCB
        self.action_counts = {}

    def get_scenario_all_desc(self, filtered_tag="feedback"):
        return "SCENARIO_DESC"

    def get_competition_full_desc(self):
        return "COMPETITION_FULL_DESC"


def make_minimal_experiment(hypothesis, based_exp_ws, based_exp_result, based_exp_sub_results):
    class ExpObj:
        pass

    exp = ExpObj()
    exp.hypothesis = hypothesis
    exp.sub_tasks = [SimpleTask("task-info")]
    exp.sub_workspace_list = [types.SimpleNamespace(all_codes="print('code')", target_task=SimpleTask("task-info"))]
    exp.experiment_workspace = types.SimpleNamespace(file_dict={})
    exp.sub_results = {"task1": 0.5}
    # Ensure DataFrame construction receives list-like values (pandas requirement)
    exp.result = {"score": [0.75]}
    be_ws = SimpleExperimentWS(
        data_description=based_exp_ws.data_description if hasattr(based_exp_ws, "data_description") else based_exp_ws,
        model_description=based_exp_ws.model_description if hasattr(based_exp_ws, "model_description") else based_exp_ws,
        file_dict=getattr(based_exp_ws, "file_dict", {}),
    )
    # ensure sota result is list-like as well
    based_exp = SimpleBasedExperiment(be_ws, {k: ([v] if not isinstance(v, (list, tuple)) else v) for k, v in based_exp_result.items()}, based_exp_sub_results)
    exp.based_experiments = [based_exp]
    return exp


def test_generate_feedback_graph_rag_and_ucb(monkeypatch):
    monkeypatch.setattr(feedback_module, "T", DummyTFactory())
    response_obj = {
        "Observations": "obs text",
        "Feedback for Hypothesis": "eval text",
        "New Hypothesis": "new hyp",
        "Reasoning": "reason text",
        "Replace Best Result": "yes",
    }
    monkeypatch.setattr(feedback_module, "APIBackend", lambda: FakeAPIBackend(response_obj))

    scen = SimpleScen(evaluation_metric_direction=True, if_using_vector_rag=False, if_using_graph_rag=True, if_action_choosing_based_on_UCB=True)
    scen.action_counts["Model tuning"] = 0
    kg_feedback = KGExperiment2Feedback(scen)

    hyp = SimpleHypothesis("try new lr", "because want better", "Model tuning")
    based_ws = SimpleExperimentWS(data_description="sota features", model_description={"m": "desc"})
    exp = make_minimal_experiment(hypothesis=hyp, based_exp_ws=based_ws, based_exp_result={"score": 0.6}, based_exp_sub_results={"sub": 0.6})

    kb = DummyKB()
    last_hyp = types.SimpleNamespace(hypothesis="previous hyp")
    trace = SimpleTrace(kb, hist=[(last_hyp, "prev feedback")])

    hf = kg_feedback.generate_feedback(exp, trace)

    assert hf.observations == "obs text"
    assert hf.hypothesis_evaluation == "eval text"
    assert hf.new_hypothesis == "new hyp"
    assert hf.reason == "reason text"
    # ensure knowledge base nodes were added (competition node excluded)
    assert len(kb.added) >= 1
    assert scen.action_counts["Model tuning"] == 1


def test_generate_feedback_vector_rag_raises(monkeypatch):
    monkeypatch.setattr(feedback_module, "T", DummyTFactory())
    response_obj = {
        "Observations": "obs2",
        "Feedback for Hypothesis": "eval2",
        "New Hypothesis": "new2",
        "Reasoning": "reason2",
        "Replace Best Result": "no",
    }
    monkeypatch.setattr(feedback_module, "APIBackend", lambda: FakeAPIBackend(response_obj))

    scen = SimpleScen(evaluation_metric_direction=False, if_using_vector_rag=True, if_using_graph_rag=False, if_action_choosing_based_on_UCB=False)
    scen.action_counts["Other"] = 0
    kg_feedback = KGExperiment2Feedback(scen)

    hyp = SimpleHypothesis("a hypothesis", "some reason", "Other")
    based_ws = SimpleExperimentWS(data_description="sota features 2", model_description={"m2": "desc2"})
    exp = make_minimal_experiment(hypothesis=hyp, based_exp_ws=based_ws, based_exp_result={"score": 0.55}, based_exp_sub_results={"sub": 0.55})
    exp.sub_workspace_list = [SimpleSubWS("task-A", "code A"), SimpleSubWS("task-B", "code B")]
    exp.sub_tasks = [SimpleTask("task-A"), SimpleTask("task-B")]

    kb = DummyKB()
    trace = SimpleTrace(kb, hist=[])

    with pytest.raises(NotImplementedError):
        kg_feedback.generate_feedback(exp, trace)
