# file: rdagent/components/coder/CoSTEER/knowledge_management.py:503-631
# asked: {"lines": [510, 511, 513, 514, 516, 518, 519, 520, 522, 524, 525, 526, 527, 529, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 549, 550, 551, 552, 553, 554, 556, 558, 559, 560, 563, 564, 565, 568, 569, 570, 573, 575, 576, 577, 578, 579, 580, 581, 582, 584, 585, 586, 588, 590, 591, 593, 594, 597, 598, 599, 600, 601, 603, 607, 608, 610, 611, 612, 613, 615, 616, 619, 620, 622, 623, 624, 626, 627, 628, 631], "branches": [[510, 511], [510, 631], [512, 516], [512, 518], [518, 519], [518, 522], [524, 525], [524, 531], [534, 536], [534, 549], [537, 534], [537, 543], [543, 544], [543, 546], [546, 537], [546, 547], [549, 550], [549, 573], [550, 549], [550, 558], [558, 559], [558, 562], [562, 550], [562, 568], [588, 589], [588, 597], [589, 588], [589, 593], [597, 598], [597, 607]]}
# gained: {"lines": [510, 511, 513, 514, 516, 518, 519, 520, 522, 524, 525, 526, 527, 529, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 549, 550, 551, 552, 553, 554, 556, 558, 559, 560, 563, 564, 565, 568, 569, 570, 573, 575, 576, 577, 578, 579, 580, 581, 582, 584, 585, 586, 588, 590, 591, 593, 594, 597, 598, 599, 600, 601, 603, 607, 608, 610, 611, 612, 613, 615, 616, 619, 620, 622, 623, 624, 626, 627, 628, 631], "branches": [[510, 511], [510, 631], [512, 516], [512, 518], [518, 519], [524, 525], [524, 531], [534, 536], [534, 549], [537, 534], [537, 543], [543, 544], [546, 537], [549, 550], [549, 573], [550, 549], [550, 558], [558, 559], [562, 568], [588, 589], [588, 597], [589, 593], [597, 598]]}

import types
import random
import builtins
import pytest

from types import SimpleNamespace

# Import the function/class under test
from rdagent.components.coder.CoSTEER import knowledge_management as km_mod
from rdagent.components.coder.CoSTEER.knowledge_management import CoSTEERQueriedKnowledgeV2


class DummyNode:
    def __init__(self, id, label):
        self.id = id
        self.label = label


class DummyFeedback:
    def __init__(self, final_decision_based_on_gt: bool):
        self.final_decision_based_on_gt = final_decision_based_on_gt


class DummyKnowledge:
    def __init__(self, name, feedback=None):
        self.name = name
        self.feedback = feedback

    def __repr__(self):
        return f"DummyKnowledge({self.name})"


class DummySubTask:
    def __init__(self, info):
        self._info = info

    def get_task_information(self):
        return self._info


class DummyKnowledgeBase:
    def __init__(self):
        # mapping from success task string -> knowledge
        self.success_task_to_knowledge_dict = {}
        # mapping from task info -> list of component nodes (IDs or node objects)
        self.task_to_component_nodes = {}
        # mapping from node id -> implementation knowledge
        self.node_to_implementation_knowledge_dict = {}
        # For control of graph queries, we store behavior
        self._by_node_map = {}
        self._by_intersection_map = {}

    def graph_query_by_node(self, node, step, constraint_labels, block):
        # Return prepared list (if node is comparable)
        # node may be DummyNode or any hashable; in our tests we use Node objects for both kinds
        return list(self._by_node_map.get(node, []))

    def graph_query_by_intersection(self, component_analysis_result, constraint_labels):
        # Return from prepared mapping keyed by tuple of component nodes
        key = tuple(component_analysis_result)
        return list(self._by_intersection_map.get(key, []))


def bind_component_query_to_obj():
    """
    Return the raw function (unbound) and a minimal instance to bind it to.
    """
    func = km_mod.CoSTEERRAGStrategyV2.component_query
    obj = SimpleNamespace()
    # attach analyze_component placeholder (can be replaced per-test)
    obj.analyze_component = lambda x: []
    return func, obj


def test_component_query_skips_when_task_in_success_or_failed():
    func, strategy_obj = bind_component_query_to_obj()

    # Build evo with two subtasks: one already in success dict, one in failed set
    sub_success = DummySubTask("task_already_success")
    sub_failed = DummySubTask("task_failed_before")
    evo = SimpleNamespace(sub_tasks=[sub_success, sub_failed])

    # Create queried_knowledge_v2 with failed_task_info_set containing one task
    qkv2 = CoSTEERQueriedKnowledgeV2(task_to_similar_task_successful_knowledge={}, task_to_former_failed_traces={}, task_to_similar_error_successful_knowledge={})
    qkv2.failed_task_info_set = {"task_failed_before"}

    # Prepare knowledgebase and attach to strategy object
    kb = DummyKnowledgeBase()
    # Put one task into success map
    kb.success_task_to_knowledge_dict["task_already_success"] = DummyKnowledge("K_success")
    strategy_obj.knowledgebase = kb

    # Bind and call
    bound = types.MethodType(func, strategy_obj)
    res = bound(evo, qkv2, v2_query_component_limit=3, knowledge_sampler=1.0)

    # Assertions: both tasks should exist as keys and map to empty lists
    assert "task_already_success" in res.task_to_similar_task_successful_knowledge
    assert res.task_to_similar_task_successful_knowledge["task_already_success"] == []
    assert "task_failed_before" in res.task_to_similar_task_successful_knowledge
    assert res.task_to_similar_task_successful_knowledge["task_failed_before"] == []


def test_component_query_full_flow_multiple_and_single_components(monkeypatch):
    func, strategy_obj = bind_component_query_to_obj()

    # Two subtasks: one will have multiple components (len>1), another single component (len==1)
    task_multi = DummySubTask("multi_task_info")
    task_single = DummySubTask("single_task_info")
    # Also one already-success task to exercise the early branch as well
    task_already = DummySubTask("already_known")
    evo = SimpleNamespace(sub_tasks=[task_multi, task_single, task_already])

    # Prepare queried knowledge v2
    qkv2 = CoSTEERQueriedKnowledgeV2(task_to_similar_task_successful_knowledge={}, task_to_former_failed_traces={}, task_to_similar_error_successful_knowledge={})
    qkv2.failed_task_info_set = set()

    # Build knowledgebase and attach behaviors
    kb = DummyKnowledgeBase()

    # Prepare component nodes as simple identifiers (could be strings or DummyNode objects)
    compA = "compA"
    compB = "compB"
    compC = "compC"

    # Set analyze_component behavior to return different lengths depending on task info
    def analyze_component(task_information):
        if task_information == "multi_task_info":
            return [compA, compB]  # len > 1 branch
        if task_information == "single_task_info":
            return [compC]  # len == 1 branch
        return []

    strategy_obj.analyze_component = analyze_component

    # Configure graph queries:
    # For compA and compB, graph_query_by_node with step=1 returns task description nodes (we'll use DummyNode)
    task_des_A = DummyNode("tdA", "task_description")
    task_des_B = DummyNode("tdB", "task_description")
    # For compC single component, no pre-intersection list
    task_des_C = DummyNode("tdC", "task_description")

    # For step=1 calls (component -> task_description), we set map for component nodes
    kb._by_node_map[compA] = [task_des_A]
    kb._by_node_map[compB] = [task_des_B]
    kb._by_node_map[compC] = [task_des_C]

    # The intersection for multi-component should be empty (so empty list returned)
    kb._by_intersection_map[tuple([compA, compB])] = []

    # For the task description nodes, when graph_query_by_node called with step=50 and constraint task_success_implement,
    # return a sequence where one node has label 'task_success_implement' and id mapping to implementation knowledge
    impl_node_A = DummyNode("implA", "task_success_implement")
    impl_node_B = DummyNode("implB", "task_success_implement")
    impl_node_C = DummyNode("implC", "task_success_implement")

    # Map each task description node to its implementation nodes list
    kb._by_node_map[task_des_A] = [impl_node_A]
    kb._by_node_map[task_des_B] = [impl_node_B]
    kb._by_node_map[task_des_C] = [impl_node_C]

    # Create Knowledge objects returned for implementation nodes
    k_impl_A = DummyKnowledge("implA", feedback=DummyFeedback(True))
    k_impl_B = DummyKnowledge("implB", feedback=None)
    k_impl_C = DummyKnowledge("implC", feedback=DummyFeedback(True))

    # node_to_implementation_knowledge_dict maps searched_node.id -> knowledge
    kb.node_to_implementation_knowledge_dict["implA"] = k_impl_A
    kb.node_to_implementation_knowledge_dict["implB"] = k_impl_B
    kb.node_to_implementation_knowledge_dict["implC"] = k_impl_C

    # Also populate success_task_to_knowledge_dict used by embedding-based addition
    kb.success_task_to_knowledge_dict = {
        "similar_task_1": DummyKnowledge("similar1", feedback=DummyFeedback(True)),
        "similar_task_2": DummyKnowledge("similar2", feedback=None),
    }

    strategy_obj.knowledgebase = kb

    # To make embedding similarity deterministic, monkeypatch calculate_embedding_distance_between_str_list
    def fake_calc(embed_targets, knowledge_base_success_task_list):
        # Return a similarity list where the first index is highest
        # length must match len(knowledge_base_success_task_list)
        return [[0.9 for _ in knowledge_base_success_task_list]]

    monkeypatch.setattr(km_mod, "calculate_embedding_distance_between_str_list", fake_calc)

    # Ensure random.uniform behavior doesn't drop items (we'll use knowledge_sampler=1.0)
    monkeypatch.setattr(random, "uniform", lambda a, b: 0.0)

    # Bind and call component_query
    bound = types.MethodType(func, strategy_obj)
    result = bound(evo, qkv2, v2_query_component_limit=3, knowledge_sampler=1.0)

    # Assertions: keys for all three tasks must exist
    assert "multi_task_info" in result.task_to_similar_task_successful_knowledge
    assert "single_task_info" in result.task_to_similar_task_successful_knowledge
    assert "already_known" in result.task_to_similar_task_successful_knowledge

    # For already_known, because it's not in kb.success_task_to_knowledge_dict nor failed set, it would have been analyzed.
    # But we didn't add analyze_component for it specifically, so it will get [] as result; ensure it's at least a key
    # (This is to ensure the loop processed it).
    # The multi task should include implementation knowledge found (k_impl_A, k_impl_B) and also embedding similar knowledge
    multi_list = result.task_to_similar_task_successful_knowledge["multi_task_info"]
    # Should include at least k_impl_A and k_impl_B (but note ordering may vary)
    # But after sampling and top-up logic with v2_query_component_limit=3, the final list length should be <=3
    assert isinstance(multi_list, list)
    assert len(multi_list) <= 3

    # Check that GT knowledge (feedback.final_decision_based_on_gt True) are prioritized:
    # For multi, k_impl_A and similar1 are both GT (similar1 has GT True), ensure at least one GT present if available
    has_gt = any(k.feedback is not None and getattr(k.feedback, "final_decision_based_on_gt", False) for k in multi_list)
    assert has_gt

    # For single task, ensure its impl knowledge is present (k_impl_C)
    single_list = result.task_to_similar_task_successful_knowledge["single_task_info"]
    assert any(k.name == "implC" for k in single_list)

    # The already_known key must exist even if empty list
    assert isinstance(result.task_to_similar_task_successful_knowledge["already_known"], list)
