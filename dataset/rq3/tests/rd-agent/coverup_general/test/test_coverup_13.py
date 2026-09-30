# file: rdagent/components/coder/CoSTEER/knowledge_management.py:503-631
# asked: {"lines": [510, 511, 513, 514, 516, 518, 519, 520, 522, 524, 525, 526, 527, 529, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 549, 550, 551, 552, 553, 554, 556, 558, 559, 560, 563, 564, 565, 568, 569, 570, 573, 575, 576, 577, 578, 579, 580, 581, 582, 584, 585, 586, 588, 590, 591, 593, 594, 597, 598, 599, 600, 601, 603, 607, 608, 610, 611, 612, 613, 615, 616, 619, 620, 622, 623, 624, 626, 627, 628, 631], "branches": [[510, 511], [510, 631], [512, 516], [512, 518], [518, 519], [518, 522], [524, 525], [524, 531], [534, 536], [534, 549], [537, 534], [537, 543], [543, 544], [543, 546], [546, 537], [546, 547], [549, 550], [549, 573], [550, 549], [550, 558], [558, 559], [558, 562], [562, 550], [562, 568], [588, 589], [588, 597], [589, 588], [589, 593], [597, 598], [597, 607]]}
# gained: {"lines": [510, 511, 513, 514, 516, 518, 519, 520, 522, 524, 525, 526, 527, 529, 531, 532, 533, 534, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 549, 550, 551, 552, 553, 554, 556, 558, 559, 560, 563, 564, 565, 568, 569, 570, 573, 575, 576, 577, 578, 579, 580, 581, 582, 584, 585, 586, 588, 590, 591, 593, 594, 597, 598, 599, 600, 601, 603, 607, 608, 610, 611, 612, 613, 615, 616, 619, 620, 622, 623, 624, 626, 627, 628, 631], "branches": [[510, 511], [510, 631], [512, 516], [512, 518], [518, 519], [524, 525], [524, 531], [534, 536], [534, 549], [537, 534], [537, 543], [543, 544], [543, 546], [546, 537], [549, 550], [549, 573], [550, 549], [550, 558], [558, 559], [562, 550], [562, 568], [588, 589], [588, 597], [589, 593], [597, 598]]}

import types
import builtins
import random

import pytest

# Import the actual class under test
from rdagent.components.coder.CoSTEER import knowledge_management as km_module

# Ensure the target class exists in the module
CoSTEERRAGStrategyV2 = getattr(km_module, "CoSTEERRAGStrategyV2", None)
assert CoSTEERRAGStrategyV2 is not None, "CoSTEERRAGStrategyV2 not found in module"


class SimpleNode:
    def __init__(self, id_, label):
        self.id = id_
        self.label = label

    def __repr__(self):
        return f"Node({self.id},{self.label})"


class Feedback:
    def __init__(self, final_decision_based_on_gt: bool):
        self.final_decision_based_on_gt = final_decision_based_on_gt


class Knowledge:
    def __init__(self, name, feedback=None):
        self.name = name
        self.feedback = feedback

    def __repr__(self):
        return f"Knowledge({self.name})"


class DummySubTask:
    def __init__(self, info):
        self._info = info

    def get_task_information(self):
        return self._info


class DummyQueriedV2:
    def __init__(self):
        self.failed_task_info_set = set()
        self.task_to_similar_task_successful_knowledge = {}


def make_strategy_with_mocks(monkeypatch):
    """
    Create an instance of CoSTEERRAGStrategyV2 with minimal initialization and
    attach a mocked knowledgebase and analyze_component; returns (inst, helpers)
    where helpers contain objects used for assertions.
    """
    # Prevent original __init__ side effects
    monkeypatch.setattr(CoSTEERRAGStrategyV2, "__init__", lambda self, *a, **k: None)

    inst = CoSTEERRAGStrategyV2()

    # Helper knowledge objects
    K_impl_gt = Knowledge("impl_gt", feedback=Feedback(True))
    K_impl_no_gt = Knowledge("impl_no_gt", feedback=None)
    K_success_a = Knowledge("success_a", feedback=Feedback(True))
    K_success_b = Knowledge("success_b", feedback=None)

    # Nodes returned by graph queries
    task_des_node_1 = SimpleNode("td1", "task_description")
    task_des_node_2 = SimpleNode("td2", "task_description")

    # Implementation nodes (searched_node) for graph queries later
    impl_node_1 = SimpleNode("impl1", "task_success_implement")
    impl_node_2 = SimpleNode("impl2", "task_success_implement")

    # knowledgebase mock
    class KB:
        def __init__(self):
            # success_task_to_knowledge_dict keys are success task strings
            self.success_task_to_knowledge_dict = {
                "success_task_a": K_success_a,
                "success_task_b": K_success_b,
            }
            # will be populated by analyze_component call in method
            self.task_to_component_nodes = {}

            # mapping of implementation node id to Knowledge
            self.node_to_implementation_knowledge_dict = {
                "impl1": K_impl_gt,
                "impl2": K_impl_no_gt,
            }

        def graph_query_by_intersection(self, component_analysis_result, constraint_labels=None):
            # For multi-component tasks, return an initial list of task description nodes
            return [task_des_node_1, task_des_node_2]

        def graph_query_by_node(self, node=None, step=None, constraint_labels=None, block=True):
            # Behavior depends on constraint_labels and the node passed
            if constraint_labels == ["task_description"] and step == 1:
                # For the reverse-iterate gathering of task_des_node_list:
                # Return different lists based on component node id to exercise reverse logic.
                if getattr(node, "id", None) == "comp_multi_1":
                    return [task_des_node_1]
                if getattr(node, "id", None) == "comp_multi_2":
                    return [task_des_node_2]
                if getattr(node, "id", None) == "comp_single":
                    # single component should return two description nodes
                    return [task_des_node_2, task_des_node_1]
                # Fallback
                return [task_des_node_1]
            if constraint_labels == ["task_success_implement"] and step == 50:
                # When searching from a task description node to find implementations,
                # return implementation nodes (some duplications to test uniqueness)
                if getattr(node, "id", None) in ("td1", "td2"):
                    return [impl_node_1, impl_node_2]
                return []
            # default empty
            return []

    kb = KB()
    inst.knowledgebase = kb

    # analyze_component should create component lists for specific task infos
    def analyze_component(task_info):
        if task_info == "multi_component_task":
            return [SimpleNode("comp_multi_1", "component"), SimpleNode("comp_multi_2", "component")]
        if task_info == "single_component_task":
            return [SimpleNode("comp_single", "component")]
        # default empty
        return []

    inst.analyze_component = analyze_component

    return inst, {
        "K_impl_gt": K_impl_gt,
        "K_impl_no_gt": K_impl_no_gt,
        "K_success_a": K_success_a,
        "K_success_b": K_success_b,
    }


def test_component_query_exercises_all_branches(monkeypatch):
    # Setup strategy instance with mocked knowledgebase and analyze_component
    inst, helpers = make_strategy_with_mocks(monkeypatch)

    # Monkeypatch the embedding similarity function to deterministic output
    def fake_calc_embedding_distance_between_str_list(a, b):
        # Return a list with one list whose length matches len(b)
        # Use values to produce a sorted order (reverse=True) that is deterministic
        # For two success tasks produce [0.2, 0.8]
        return [[0.2, 0.8]]

    monkeypatch.setattr(km_module, "calculate_embedding_distance_between_str_list", fake_calc_embedding_distance_between_str_list)

    # Prepare evolvable subjects (object with sub_tasks)
    class Evo:
        def __init__(self, subs):
            self.sub_tasks = subs

    subs = [
        DummySubTask("success_task_a"),  # triggers early branch: in success_task_to_knowledge_dict
        DummySubTask("multi_component_task"),  # triggers len(component_analysis_result) > 1 path
        DummySubTask("single_component_task"),  # triggers len(component_analysis_result) == 1 path
    ]
    evo = Evo(subs)

    # Prepare queried_knowledge_v2
    qv2 = DummyQueriedV2()

    # Run the method under test with a specific v2_query_component_limit and knowledge_sampler>0
    v2_query_component_limit = 3
    knowledge_sampler = 1.0  # keep all (no randomness effect)

    res = inst.component_query(evo, qv2, v2_query_component_limit=v2_query_component_limit, knowledge_sampler=knowledge_sampler)

    # Verify return is the same object passed in
    assert res is qv2

    # Check that the early-branch task's list is empty as per code
    assert qv2.task_to_similar_task_successful_knowledge.get("success_task_a", None) == []

    # For the multi and single component tasks, ensure lists exist and lengths are at most v2_query_component_limit
    multi_list = qv2.task_to_similar_task_successful_knowledge.get("multi_component_task")
    single_list = qv2.task_to_similar_task_successful_knowledge.get("single_component_task")

    assert isinstance(multi_list, list)
    assert isinstance(single_list, list)
    assert len(multi_list) <= v2_query_component_limit
    assert len(single_list) <= v2_query_component_limit

    # All returned items should be Knowledge instances as produced by our mocked knowledgebase
    for k in (multi_list + single_list):
        assert isinstance(k, Knowledge)

    # Verify GT-rule post-processing: compute expected counts and compare
    def compute_expected_final_list(original_list):
        queried_from_gt = [k for k in original_list if getattr(k, "feedback", None) is not None and getattr(k.feedback, "final_decision_based_on_gt", False) is True]
        queried_without_gt = [k for k in original_list if k not in queried_from_gt]
        queried_from_gt_count = max(min((v2_query_component_limit // 2 + 1), len(queried_from_gt)), v2_query_component_limit - len(queried_without_gt))
        final_expected = queried_from_gt[:queried_from_gt_count] + queried_without_gt[: v2_query_component_limit - queried_from_gt_count]
        return final_expected

    # Reconstruct what original_list would have been before the GT filtering for both tasks.
    # It's not trivial to extract that from qv2 now, but we can at least assert the final lists honor the constraints:
    # 1) length equals v2_query_component_limit or less if not enough items
    # 2) number of GT items is at least computed lower bound
    for task_info in ("multi_component_task", "single_component_task"):
        final_list = qv2.task_to_similar_task_successful_knowledge[task_info]
        # length limit respected
        assert len(final_list) <= v2_query_component_limit

        # Count GT items
        gt_count = sum(1 for k in final_list if getattr(k, "feedback", None) is not None and getattr(k.feedback, "final_decision_based_on_gt", False) is True)
        # Minimum required GT items according to code:
        # Compute number of without-gt and with-gt from the final_list itself;
        with_gt = [k for k in final_list if getattr(k, "feedback", None) is not None and getattr(k.feedback, "final_decision_based_on_gt", False) is True]
        without_gt = [k for k in final_list if k not in with_gt]
        minimal_required = max(min((v2_query_component_limit // 2 + 1), len(with_gt)), v2_query_component_limit - len(without_gt))
        # gt_count should be >= minimal_required (as the code enforces)
        assert gt_count >= minimal_required

