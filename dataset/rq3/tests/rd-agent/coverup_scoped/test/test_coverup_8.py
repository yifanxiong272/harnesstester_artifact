# file: rdagent/components/coder/CoSTEER/knowledge_management.py:633-759
# asked: {"lines": [640, 641, 642, 644, 645, 647, 649, 651, 652, 653, 655, 656, 658, 659, 661, 662, 663, 665, 667, 668, 669, 670, 671, 672, 673, 675, 676, 677, 678, 679, 681, 683, 684, 685, 687, 688, 689, 690, 691, 692, 693, 694, 695, 696, 697, 698, 714, 715, 716, 717, 718, 719, 720, 725, 728, 729, 731, 733, 734, 735, 737, 738, 739, 740, 741, 742, 743, 747, 748, 749, 750, 751, 754, 755, 756, 759], "branches": [[640, 641], [640, 759], [643, 647], [643, 649], [650, 655], [650, 665], [668, 669], [668, 675], [669, 670], [669, 673], [671, 672], [671, 673], [675, 676], [675, 683], [685, 687], [685, 714], [688, 685], [688, 694], [694, 695], [694, 697], [697, 688], [697, 698], [716, 717], [716, 747], [717, 716], [717, 727], [727, 717], [727, 731], [738, 739], [738, 740], [747, 748], [747, 754]]}
# gained: {"lines": [640, 641, 642, 644, 645, 647, 649, 651, 652, 653, 655, 656, 658, 659, 661, 662, 663, 667, 668, 669, 670, 671, 673, 675, 676, 677, 678, 679, 681, 685, 687, 688, 689, 690, 691, 692, 693, 694, 695, 696, 697, 714, 715, 716, 717, 718, 719, 720, 725, 728, 729, 731, 733, 734, 735, 737, 738, 739, 740, 741, 742, 743, 747, 748, 749, 750, 751, 754, 755, 756, 759], "branches": [[640, 641], [640, 759], [643, 647], [643, 649], [650, 655], [668, 669], [668, 675], [669, 670], [671, 673], [675, 676], [685, 687], [685, 714], [688, 685], [688, 694], [694, 695], [697, 688], [716, 717], [716, 747], [717, 716], [717, 727], [727, 717], [727, 731], [738, 739], [738, 740], [747, 748]]}

import importlib
import pytest
from types import SimpleNamespace

km = importlib.import_module("rdagent.components.coder.CoSTEER.knowledge_management")
CoSTEERRAGStrategyV2 = km.CoSTEERRAGStrategyV2

class DummyTask:
    def __init__(self, info):
        self._info = info
    def get_task_information(self):
        return self._info

class DummyQueriedKnowledgeV2:
    def __init__(self):
        # initialize as expected by the method
        self.task_to_similar_error_successful_knowledge = {}
        self.task_to_former_failed_traces = {}
        self.failed_task_info_set = set()

def make_fake_self(monkeypatch, graph_funcs):
    """
    Create a fake 'self' object with a knowledgebase attribute that implements
    the methods and dicts used by error_query.
    graph_funcs: dict with keys:
        - graph_get_node_by_content
        - graph_query_by_intersection
        - graph_query_by_node
    Returns a fake self object.
    """
    kb = SimpleNamespace()
    # default empty dicts, can be overwritten by caller
    kb.success_task_to_knowledge_dict = {}
    kb.working_trace_error_analysis = {}
    kb.working_trace_knowledge = {}
    kb.node_to_implementation_knowledge_dict = {}
    # attach graph functions
    kb.graph_get_node_by_content = graph_funcs["graph_get_node_by_content"]
    kb.graph_query_by_intersection = graph_funcs["graph_query_by_intersection"]
    kb.graph_query_by_node = graph_funcs["graph_query_by_node"]

    fake_self = SimpleNamespace()
    fake_self.knowledgebase = kb

    return fake_self

def test_error_query_when_task_in_success_or_failed(monkeypatch):
    """
    Test branch where target_task_information is present in success_task_to_knowledge_dict
    and also when present in failed_task_info_set. The method should set empty lists.
    """
    # create fake self with minimal knowledgebase
    def dummy_get_node_by_content(content):
        return None
    def dummy_query_intersection(*args, **kwargs):
        return []
    def dummy_query_by_node(*args, **kwargs):
        return []

    fake_self = make_fake_self(monkeypatch, {
        "graph_get_node_by_content": dummy_get_node_by_content,
        "graph_query_by_intersection": dummy_query_intersection,
        "graph_query_by_node": dummy_query_by_node,
    })

    # prepare evo with one task
    task_info = "task_alpha"
    evo = SimpleNamespace(sub_tasks=[DummyTask(task_info)])

    # case A: present in success_task_to_knowledge_dict
    fake_self.knowledgebase.success_task_to_knowledge_dict = {task_info: ["some_knowledge"]}
    qk = DummyQueriedKnowledgeV2()
    # ensure not in failed set
    qk.failed_task_info_set = set()
    res = CoSTEERRAGStrategyV2.error_query(fake_self, evo, qk)
    # verify mutated dict and return object
    assert isinstance(res, DummyQueriedKnowledgeV2)
    assert res.task_to_similar_error_successful_knowledge[task_info] == []

    # case B: present in failed_task_info_set instead
    fake_self.knowledgebase.success_task_to_knowledge_dict = {}
    qk2 = DummyQueriedKnowledgeV2()
    qk2.failed_task_info_set = {task_info}
    res2 = CoSTEERRAGStrategyV2.error_query(fake_self, evo, qk2)
    assert res2.task_to_similar_error_successful_knowledge[task_info] == []

def test_error_query_full_path_with_multiple_error_nodes(monkeypatch):
    """
    Exercise the main branch where:
    - working_trace_error_analysis and working_trace_knowledge are set
    - graph_get_node_by_content converts error identifiers to node objects
    - graph_query_by_intersection returns initial intersections
    - graph_query_by_node returns trace nodes and success nodes
    Verify resulting sampled knowledge list is created correctly and deterministic via monkeypatched random.uniform.
    """
    # Define a simple Node class for the test
    class Node:
        _id_counter = 0
        def __init__(self, content="", label=""):
            type(self)._id_counter += 1
            self.id = type(self)._id_counter
            self.content = content
            self.label = label
        def __repr__(self):
            return f"Node(id={self.id}, content={self.content}, label={self.label})"
        def __eq__(self, other):
            return getattr(other, "id", None) == getattr(self, "id", None)
        def __hash__(self):
            return hash(self.id)

    # Monkeypatch the module's UndirectedNode to our test Node to satisfy isinstance checks if any
    monkeypatch.setattr(km, "UndirectedNode", Node, raising=False)

    # Create nodes we'll use
    err1_node = Node(content="err1", label="component_error")
    err2_node = Node(content="err2", label="component_error")
    trace_node = Node(content="trace_node", label="task_trace")
    trace_node_intersect = Node(content="trace_intersect", label="task_trace")
    success_node = Node(content="success_impl", label="task_success_implement")
    other_node = Node(content="other", label="task_description")

    # Implement graph functions
    def graph_get_node_by_content(content):
        if content == "err1":
            return err1_node
        if content == "err2":
            return err2_node
        return None

    # For intersection: return an initial entry linking both error nodes to trace_node_intersect
    def graph_query_by_intersection(error_nodes, constraint_labels=None, output_intersection_origin=False):
        # return list of pairs ([error_nodes], trace_node_intersect)
        return [[error_nodes, trace_node_intersect]]

    # For graph_query_by_node: behavior depends on node argument
    def graph_query_by_node(node, step=1, constraint_labels=None, block=False):
        # If called with an error node, return task trace nodes (simulate reverse iterate)
        if getattr(node, "content", None) in ("err1", "err2"):
            return [trace_node]
        # If called with a trace node for deep search (step=50), return nodes including a success implement node
        if getattr(node, "label", None) == "task_trace" and step >= 50:
            return [other_node, success_node]
        return []

    fake_self = make_fake_self(monkeypatch, {
        "graph_get_node_by_content": graph_get_node_by_content,
        "graph_query_by_intersection": graph_query_by_intersection,
        "graph_query_by_node": graph_query_by_node,
    })

    # Prepare working traces and error analyses
    task_info = "task_beta"
    traceA = ("step1", "step2")
    fake_self.knowledgebase.working_trace_knowledge = {
        task_info: [traceA]
    }
    fake_self.knowledgebase.working_trace_error_analysis = {
        task_info: [["err1", "err2"]]
    }

    # Map nodes to implementation knowledge objects
    fake_self.knowledgebase.node_to_implementation_knowledge_dict = {
        trace_node.id: {"impl": "trace_impl"},
        trace_node_intersect.id: {"impl": "trace_impl_intersect"},
        success_node.id: {"impl": "success_impl"},
        other_node.id: {"impl": "other_impl"},
    }

    # Prepare evo with one task
    evo = SimpleNamespace(sub_tasks=[DummyTask(task_info)])

    # Prepare queried_knowledge_v2 with a former failed trace matching traceA
    qk = DummyQueriedKnowledgeV2()
    qk.task_to_former_failed_traces[task_info] = [[traceA]]
    qk.failed_task_info_set = set()

    # Ensure deterministic inclusion: monkeypatch module's random.uniform to return 0.0 (<=1.0)
    monkeypatch.setattr(km.random, "uniform", lambda a, b: 0.0)

    # Call error_query with a limit that results in small single_error_constraint
    res = CoSTEERRAGStrategyV2.error_query(fake_self, evo, qk, v2_query_error_limit=3, knowledge_sampler=1.0)

    # Verify results were stored
    assert task_info in res.task_to_similar_error_successful_knowledge
    results = res.task_to_similar_error_successful_knowledge[task_info]
    assert isinstance(results, list)
    assert len(results) >= 1

    # Validate structure and contents for the first result
    error_content, (trace_k, success_k) = results[0]
    assert "err" in error_content
    assert trace_k in fake_self.knowledgebase.node_to_implementation_knowledge_dict.values()
    assert success_k in fake_self.knowledgebase.node_to_implementation_knowledge_dict.values()

    # Verify that filtering by sampler works: set sampler small positive and random.uniform to return 1.0 so items are filtered out
    qk2 = DummyQueriedKnowledgeV2()
    qk2.task_to_former_failed_traces[task_info] = [[traceA]]
    qk2.failed_task_info_set = set()
    # monkeypatch random.uniform to return a value > any sampler to force filtering
    monkeypatch.setattr(km.random, "uniform", lambda a, b: 1.0)
    res2 = CoSTEERRAGStrategyV2.error_query(fake_self, evo, qk2, v2_query_error_limit=5, knowledge_sampler=0.5)
    assert res2.task_to_similar_error_successful_knowledge[task_info] == []
