import types
import importlib

import pytest


GRAPH_MOD = importlib.import_module("rdagent.scenarios.kaggle.knowledge_management.graph")
KGKnowledgeGraph = getattr(GRAPH_MOD, "KGKnowledgeGraph")


class MockNode:
    def __init__(self, *args, **kwargs):
        # Accept content= and label= kwargs as in the real constructor
        self.content = kwargs.get("content") if "content" in kwargs else (args[0] if args else None)
        self.label = kwargs.get("label")

    def __repr__(self):
        return f"MockNode(content={self.content!r}, label={self.label!r})"


def _make_instance_and_patch(module, knowledge_list_list):
    """
    Create a KGKnowledgeGraph instance without running its real __init__,
    patch module-level collaborators (UndirectedNode, multiprocessing_wrapper, tqdm),
    and return (instance, recorded_added_pairs)
    """
    # Patch UndirectedNode used inside load_from_documents
    module.UndirectedNode = MockNode

    # Patch multiprocessing_wrapper to return our prepared knowledge_list_list
    def fake_multiprocessing_wrapper(tasks, n=None, **kwargs):
        # ignore tasks, return the prepared structure
        return knowledge_list_list

    module.multiprocessing_wrapper = fake_multiprocessing_wrapper

    # Patch tqdm to be identity iterator
    module.tqdm = lambda x: x

    # Create a bare instance without invoking __init__ to avoid unknown constructor requirements
    instance = object.__new__(KGKnowledgeGraph)

    # batch_embedding should just return the list passed through (simulate embeddings added)
    instance.batch_embedding = lambda node_list: node_list

    # record add_node calls
    recorded = []

    def fake_add_node(node, competition_node):
        recorded.append((node, competition_node))

    instance.add_node = fake_add_node

    return instance, recorded


def test_load_from_documents_creates_nodes_for_complete_knowledge_round_071():
    # Arrange: one document producing one knowledge dict with full fields
    knowledge = {
        "competition": "KaggleComp",
        "hypothesis": {"type": "H1", "detail": "some hypothesis"},
        "experiments": "exp-results",
        "code": "print(1)",
        "conclusion": "we conclude",
    }
    knowledge_list_list = [[knowledge]]

    instance, recorded = _make_instance_and_patch(GRAPH_MOD, knowledge_list_list)

    # Act
    instance.load_from_documents(["doc1 content"], None)

    # Assert: one competition node and four action nodes paired -> add_node called 4 times
    assert len(recorded) == 4, f"expected 4 node pairs added, got {len(recorded)}"

    # Check that competition node content was preserved and labels of action nodes are correct
    for node, comp in recorded:
        assert isinstance(node, MockNode)
        assert isinstance(comp, MockNode)
        assert comp.label == "competition"
        assert comp.content == "KaggleComp"

    # Check specific labels order and contents (hypothesis first)
    labels = [pair[0].label for pair in recorded]
    contents = [pair[0].content for pair in recorded]

    assert labels[0] == "H1"
    assert "exp-results" in contents
    assert any(c == "print(1)" for c in contents)
    assert any(c == "we conclude" for c in contents)


def test_load_from_documents_hypothesis_na_skips_action_nodes_round_071():
    # Arrange: hypothesis is a string 'N/A' -> inner action loop should break and no action nodes added
    knowledge = {
        "competition": "",
        "hypothesis": "N/A",
        "experiments": "exp-should-not-be-linked",
    }
    knowledge_list_list = [[knowledge]]

    instance, recorded = _make_instance_and_patch(GRAPH_MOD, knowledge_list_list)

    # Act
    instance.load_from_documents(["doc2"], None)

    # Assert: competition node may be created internally but node_pairs should be empty and add_node not called
    assert recorded == [], f"expected no add_node calls when hypothesis is 'N/A', got {recorded}"


def test_load_from_documents_encounters_empty_dict_breaks_inner_loop_round_071():
    # Arrange: first knowledge in a knowledge_list is {} -> should break inner loop and skip remaining entries
    useful_knowledge = {
        "competition": "CompShouldNotBeProcessed",
        "hypothesis": {"type": "ShouldNotAppear"},
        "experiments": "exp1",
    }
    # The knowledge_list for the single document contains an empty dict first, then a useful one
    knowledge_list_list = [[{}, useful_knowledge]]

    instance, recorded = _make_instance_and_patch(GRAPH_MOD, knowledge_list_list)

    # Act
    instance.load_from_documents(["doc3"], None)

    # Assert: because the first knowledge dict is empty, the rest of that knowledge_list is not processed
    assert recorded == [], "expected no nodes to be added when an empty knowledge dict appears first in a list"
