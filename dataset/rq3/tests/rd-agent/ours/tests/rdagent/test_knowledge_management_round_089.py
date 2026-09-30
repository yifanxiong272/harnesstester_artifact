import builtins
from dataclasses import dataclass
from typing import List

from rdagent.components.coder.CoSTEER.knowledge_management import CoSTEERKnowledgeBaseV2

# Deterministic lightweight node type for tests
@dataclass(eq=True, frozen=True)
class DummyNode:
    name: str

    def __repr__(self):
        return f"DummyNode({self.name!r})"

class MockGraph:
    """Mock graph that deterministically returns the first node of the provided node_list.

    This deterministic mapping produces repeated intersection results across combinations
    so the function under test will exercise deduplication and origin-list-building branches.
    """
    def get_nodes_intersection(self, node_list: List[DummyNode], steps=None, constraint_labels=None):
        # Always return a single-element list containing the first element of node_list
        # to create duplicates across different combinations in a predictable way.
        return [node_list[0]]


def _make_kb_with_mock_graph():
    # Bypass any heavy constructor logic by creating an instance without __init__
    inst = object.__new__(CoSTEERKnowledgeBaseV2)
    inst.graph = MockGraph()
    return inst


def test_graph_query_by_intersection_unique_no_origin_round_089():
    """When output_intersection_origin is False, the result should be a deduplicated
    list of nodes preserving first-seen order."""
    kb = _make_kb_with_mock_graph()

    a = DummyNode("A")
    b = DummyNode("B")
    c = DummyNode("C")

    # With nodes [A,B,C] and MockGraph returning [first_node] per combo, the
    # flattened intersection list becomes [A, A, A, B] and deduplication yields [A, B].
    result = kb.graph_query_by_intersection([a, b, c], steps=1, constraint_labels=None, output_intersection_origin=False)

    assert isinstance(result, list)
    assert result == [a, b]


def test_graph_query_by_intersection_with_origin_round_089():
    """When output_intersection_origin is True, each returned intersection node
    is paired with an origin node_list from the internal origin_list built by the function.

    This test asserts the exact pairing behavior produced by the implementation's
    origin_list indexing logic for a deterministic MockGraph.
    """
    kb = _make_kb_with_mock_graph()

    a = DummyNode("A")
    b = DummyNode("B")
    c = DummyNode("C")

    result = kb.graph_query_by_intersection([a, b, c], steps=1, constraint_labels=None, output_intersection_origin=True)

    # The implementation appends origin_list entries in a cumulative, predictable way
    # (see test analysis). For our MockGraph (returning node_list[0] each time), the
    # flattened intersection_node_list will be [A, A, A, B] and origin_list will have
    # corresponding entries at indices 0..3 as below.
    expected = [
        [[a, b, c], a],  # from k=3 combination
        [[a, b], a],     # first of the two appends from (A,B)
        [[a, b], a],     # second of the two appends from (A,B)
        [[a, c], b],     # mapped according to the implementation's origin indexing
    ]

    assert isinstance(result, list)
    # Ensure structure and content equality (Dataclass equality makes this deterministic)
    assert result == expected
