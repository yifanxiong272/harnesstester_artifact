import types
import builtins
import random
import pytest

import rdagent.components.coder.CoSTEER.knowledge_management as km


class FakeNode:
    def __init__(self, id, label, content=None):
        self.id = id
        self.label = label
        self.content = content


class FakeKnowledge:
    def __init__(self, name, feedback=None):
        self.name = name
        self.feedback = feedback

    def __repr__(self):
        return f"FakeKnowledge({self.name})"


class FakeFeedback:
    def __init__(self, final_decision_based_on_gt=None):
        self.final_decision_based_on_gt = final_decision_based_on_gt


class FakeSubTask:
    def __init__(self, info):
        self._info = info

    def get_task_information(self):
        return self._info


class FakeEvo:
    def __init__(self, infos):
        self.sub_tasks = [FakeSubTask(i) for i in infos]


class FakeQueriedV2:
    def __init__(self, failed_task_info_set=None):
        self.failed_task_info_set = set(failed_task_info_set or [])
        self.task_to_similar_task_successful_knowledge = {}


class FakeKnowledgeBase:
    def __init__(self):
        # one ground-truth success mapping used by embedding part
        self.success_task_to_knowledge_dict = {"gt_task": FakeKnowledge("gt_knowledge", feedback=FakeFeedback(final_decision_based_on_gt=True))}
        self.failed_task_info_set = set()
        self.task_to_component_nodes = {}
        # map node.id -> knowledge for implementation nodes
        self.node_to_implementation_knowledge_dict = {}
        self.intersection_called = False
        self.intersection_inputs = None

    def graph_query_by_intersection(self, nodes, steps=None, constraint_labels=None, output_intersection_origin=False):
        # Record call and return a short list to simulate intersection found
        self.intersection_called = True
        self.intersection_inputs = (tuple(nodes), tuple(constraint_labels or []))
        # Return a single 'task_description' node to seed the later loops
        return [FakeNode("td_intersect", "task_description")]

    def graph_query_by_node(self, node=None, step=None, constraint_labels=None, block=None, constraint_node=None, constraint_distance=None):
        # Two behaviors depending on constraint_labels
        labels = constraint_labels or []
        if "task_description" in labels:
            # Return some description nodes. Use different nodes per component node id for variety.
            base = getattr(node, "id", str(node))
            return [
                FakeNode(f"{base}_desc_1", "task_description"),
                FakeNode(f"{base}_desc_2", "task_description"),
            ]
        if "task_success_implement" in labels:
            # Return nodes that include at least one implementation node
            impl1 = FakeNode("impl_1", "task_success_implement")
            impl2 = FakeNode("impl_2", "other_label")
            # Map impl_1 to a knowledge object
            self.node_to_implementation_knowledge_dict[impl1.id] = FakeKnowledge("impl_knowledge", feedback=None)
            return [impl1, impl2]
        # default
        return []


@pytest.fixture(autouse=True)
def patch_embeddings_and_random(monkeypatch):
    # Patch embedding similarity to deterministic values and patch random.uniform
    def fake_embedding(a, b):
        # Return a list of similarity lists where gt_task has moderate similarity
        # Ensure deterministic ordering
        return [[0.5 for _ in (b or [])][:len(b)]] if isinstance(b, list) and len(b) > 0 else [[0.5]]

    monkeypatch.setattr(km, "calculate_embedding_distance_between_str_list", lambda a, b: [[0.5 for _ in (b or [])][:len(b)] if isinstance(b, list) and len(b) > 0 else [0.5]])
    # deterministic random: always return 0.0 so that <= knowledge_sampler is True when sampler>0
    monkeypatch.setattr(km.random, "uniform", lambda a, b: 0.0)
    yield


def _prepare_strategy_with_fake_kb():
    # Create a CoSTEERRAGStrategyV2 without invoking heavy __init__
    StrategyCls = km.CoSTEERRAGStrategyV2
    strat = object.__new__(StrategyCls)
    # attach a fake knowledgebase and a simple analyze_component implementation
    kb = FakeKnowledgeBase()

    def analyze_component(self, target_task_information):
        # Provide different component node lists depending on the task info
        if target_task_information == "t_multicomp":
            # two components to exercise the intersection branch
            comp_a = FakeNode("compA", "component")
            comp_b = FakeNode("compB", "component")
            return [comp_a, comp_b]
        if target_task_information == "t_singlecomp":
            # single component to exercise the single-component branch
            comp_s = FakeNode("compS", "component")
            return [comp_s]
        # default empty
        return []

    strat.knowledgebase = kb
    # bind analyze_component as a method on this instance
    strat.analyze_component = types.MethodType(analyze_component, strat)
    return strat


def test_component_query_handles_success_and_multi_and_single_components_round_033():
    strat = _prepare_strategy_with_fake_kb()
    kb = strat.knowledgebase

    # Prepare some known tasks:
    # 1) task already in success -> should be set to [] and not processed further
    success_task_info = "t_success"
    kb.success_task_to_knowledge_dict[success_task_info] = FakeKnowledge("from_gt", feedback=FakeFeedback(final_decision_based_on_gt=True))

    # 2) task that will exercise multi-component path
    multi_info = "t_multicomp"

    # 3) task that will exercise single-component path
    single_info = "t_singlecomp"

    # Build evo with three subtasks in order
    evo = FakeEvo([success_task_info, multi_info, single_info])

    queried = FakeQueriedV2()

    # Ensure initial maps are empty to let component_query populate them
    queried.task_to_similar_task_successful_knowledge = {}

    # Now call component_query with a small component limit so branches are deterministic
    result = strat.component_query(evo, queried, v2_query_component_limit=3, knowledge_sampler=1.0)

    # The function returns the same queried object
    assert result is queried

    # Assert the success task key exists and is an empty list as per early branch
    assert success_task_info in queried.task_to_similar_task_successful_knowledge
    assert queried.task_to_similar_task_successful_knowledge[success_task_info] == []

    # For the multi component task, we expect it to be present and contain at least the implementation knowledge
    assert multi_info in queried.task_to_similar_task_successful_knowledge
    multi_list = queried.task_to_similar_task_successful_knowledge[multi_info]
    # Because our fake graph_query_by_node maps impl_1 to an impl_knowledge, that object should be present
    assert any(isinstance(k, FakeKnowledge) and k.name == "impl_knowledge" for k in multi_list)

    # Also because we had gt_task in the knowledgebase, embedding-based addition should append that knowledge
    assert any(isinstance(k, FakeKnowledge) and k.name == "gt_knowledge" for k in multi_list)

    # For the single component task, similar expectations: we should have entries (possibly including impl_knowledge and gt knowledge)
    assert single_info in queried.task_to_similar_task_successful_knowledge
    single_list = queried.task_to_similar_task_successful_knowledge[single_info]
    assert any(isinstance(k, FakeKnowledge) for k in single_list)

    # Ensure no list exceeds the component limit
    for key, lst in queried.task_to_similar_task_successful_knowledge.items():
        assert len(lst) <= 3


def test_component_query_respects_failed_and_sampler_logic_round_033():
    strat = _prepare_strategy_with_fake_kb()
    kb = strat.knowledgebase

    # Setup: mark a task as failed -> should be short-circuited and set to []
    failed_info = "t_failed"
    queried = FakeQueriedV2(failed_task_info_set=[failed_info])
    evo = FakeEvo([failed_info])
    queried.task_to_similar_task_successful_knowledge = {}

    # call with knowledge_sampler less than 1 but our patched random.uniform returns 0.0
    result = strat.component_query(evo, queried, v2_query_component_limit=2, knowledge_sampler=0.1)
    assert result is queried
    assert failed_info in queried.task_to_similar_task_successful_knowledge
    assert queried.task_to_similar_task_successful_knowledge[failed_info] == []


if __name__ == "__main__":
    pytest.main([__file__])
