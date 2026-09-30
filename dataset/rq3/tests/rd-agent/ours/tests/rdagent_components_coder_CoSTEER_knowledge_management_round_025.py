import types
from types import SimpleNamespace

from rdagent.components.coder.CoSTEER import knowledge_management as km


class _Node:
    def __init__(self, content, id_, label=None):
        self.content = content
        self.id = id_
        self.label = label


class DummyTask:
    def __init__(self, info):
        self._info = info

    def get_task_information(self):
        return self._info


def test_error_query_success_present_round_025():
    # Create a dummy self-like object with a knowledgebase that signals success exists
    class KB:
        def __init__(self):
            # target task is considered already successful
            self.success_task_to_knowledge_dict = {"task-success": ["k1"]}
            # not used in this scenario but must exist
            self.working_trace_error_analysis = {}
            self.working_trace_knowledge = {}
            self.node_to_implementation_knowledge_dict = {}

            # graph operations should not be invoked for this branch
        def graph_get_node_by_content(self, content):
            raise AssertionError("graph_get_node_by_content should not be called in success-present branch")

        def graph_query_by_intersection(self, *args, **kwargs):
            raise AssertionError("graph_query_by_intersection should not be called in success-present branch")

        def graph_query_by_node(self, *args, **kwargs):
            raise AssertionError("graph_query_by_node should not be called in success-present branch")

    dummy_self = SimpleNamespace()
    dummy_self.knowledgebase = KB()

    evo = SimpleNamespace()
    evo.sub_tasks = [DummyTask("task-success")]

    queried = SimpleNamespace()
    # Must include structures that error_query expects
    queried.task_to_former_failed_traces = {"task-success": []}
    queried.task_to_similar_error_successful_knowledge = {}
    queried.failed_task_info_set = set()

    # Call the method under test
    out = km.CoSTEERRAGStrategyV2.error_query(dummy_self, evo, queried, v2_query_error_limit=3, knowledge_sampler=0)

    # Oracle: when the task is present in success_task_to_knowledge_dict, mapping is set to []
    assert out is queried
    assert out.task_to_similar_error_successful_knowledge.get("task-success") == []


def test_error_query_with_two_error_nodes_round_025():
    # Build a knowledgebase that simulates two error nodes resolving to two task-trace relationships
    class KB:
        def __init__(self):
            self.success_task_to_knowledge_dict = {}

            # working_trace_knowledge contains trace ids; the former failed traces will point to one of them
            self.working_trace_knowledge = {"task-A": ["trace-1"]}

            # For each trace in working_trace_knowledge, we have an associated error analysis list
            # working_trace_error_analysis['task-A'][0] should be consumed as last_knowledge_error_analysis_result
            self.working_trace_error_analysis = {"task-A": [["errX", "errY"]]}

            # mapping node.id -> some implementation knowledge (opaque to this function)
            self.node_to_implementation_knowledge_dict = {}

            # Provide a simple intersection result (list of pairs (error_node_list, trace_node))
            # The error nodes used in the intersection results will be _Node instances returned by graph_get_node_by_content
            self._trace_node_from_intersection = _Node("trace-node-intersect", "trace-node-intersect-id", label="task_trace")

            # The success node which will be discovered by graph_query_by_node (with step=50)
            self._success_node = _Node("success-impl", "success-id", label="task_success_implement")

            # map implementation knowledge for trace and success nodes
            self.node_to_implementation_knowledge_dict[self._trace_node_from_intersection.id] = "trace_impl_k"
            self.node_to_implementation_knowledge_dict[self._success_node.id] = "success_impl_k"

        def graph_get_node_by_content(self, content):
            # Return a Node object for any error content
            return _Node(content, f"id-{content}", label="error")

        def graph_query_by_intersection(self, nodes, *args, **kwargs):
            # Return one pair: ([error_nodes], trace_node)
            # error nodes should be the objects in 'nodes' param; we pick one trace node
            return [([nodes[0], nodes[1]], self._trace_node_from_intersection)]

        def graph_query_by_node(self, node, step=1, *args, **kwargs):
            # Behavior depends on the 'step' parameter as used in function under test
            if step == 1:
                # For reverse-iteration loop: return a trace node not present in intersection list so it will be appended
                return [ _Node("trace-from-error-node", "trace-from-error-node-id", label="task_trace") ]
            elif step == 50:
                # For deeper search from the trace node, return the success implementation node
                return [ self._success_node ]
            else:
                return []

    kb = KB()

    dummy_self = SimpleNamespace()
    dummy_self.knowledgebase = kb

    # Evo with one subtask
    evo = SimpleNamespace()
    evo.sub_tasks = [DummyTask("task-A")]

    # queried_knowledge_v2 must contain a former failed trace whose last element matches trace-1
    queried = SimpleNamespace()
    # the code takes queried.task_to_former_failed_traces[target_task_information][0][-1]
    # so provide a nested list whose last element is 'trace-1'
    queried.task_to_former_failed_traces = {"task-A": [["trace-1"]]}
    queried.task_to_similar_error_successful_knowledge = {}
    queried.failed_task_info_set = set()

    # Call the method under test with knowledge_sampler > 0 to exercise sampling path (sampling uses <= knowledge_sampler)
    out = km.CoSTEERRAGStrategyV2.error_query(dummy_self, evo, queried, v2_query_error_limit=5, knowledge_sampler=1.0)

    # Oracle: resulting mapping should contain an entry for 'task-A' with list of pairs
    assert out is queried
    result_list = out.task_to_similar_error_successful_knowledge.get("task-A")
    # It should be a list (possibly empty if something failed), but in our setup it should contain at least one pair
    assert isinstance(result_list, list)
    assert len(result_list) >= 1

    # Validate structure of the first returned pair: (error_content_str, (trace_knowledge, success_knowledge))
    first = result_list[0]
    assert isinstance(first, tuple) and len(first) == 2
    error_content, knowledge_pair = first
    assert isinstance(error_content, str) and "err" in error_content
    assert isinstance(knowledge_pair, tuple) and len(knowledge_pair) == 2
    # The trace and success implementation knowledge should match those we injected
    assert knowledge_pair[0] == "trace_impl_k"
    assert knowledge_pair[1] == "success_impl_k"
