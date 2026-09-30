import importlib
from types import SimpleNamespace

import pytest

MODULE_PATH = (
    "rdagent.scenarios.data_science.proposal.exp_gen.idea_pool"
)


class FakeNode:
    def __init__(self, *, content=None, label=None, appendix=None):
        # mirror the kwargs used by the original code so tests can assert on them
        self.content = content
        self.label = label
        self.appendix = appendix

    def __repr__(self):
        return f"FakeNode(content={self.content!r}, label={self.label!r}, appendix={self.appendix!r})"


class IdeaMock:
    def __init__(self, idea, competition=None, hypothesis=None, name_str=None):
        self.idea = idea
        self.competition = competition
        self.hypothesis = {} if hypothesis is None else dict(hypothesis)
        # allow deterministic appendix via __str__
        self._name_str = "<IdeaMock>" if name_str is None else name_str

    def __str__(self):
        return self._name_str


@pytest.fixture(autouse=True)
def reload_and_patch_module(monkeypatch):
    """Import the target module freshly and patch UndirectedNode to a local lightweight FakeNode.

    We patch the symbol where the code under test resolves it (module-level name), ensuring
    no dependency on the real graph implementation or external I/O. Tests then create
    DSKnowledgeBase instances without invoking heavy initialization.
    """
    mod = importlib.import_module(MODULE_PATH)
    importlib.reload(mod)

    # Patch the UndirectedNode symbol used by add_idea
    monkeypatch.setattr(mod, "UndirectedNode", FakeNode, raising=True)

    return mod


def _make_db_instance(mod):
    # Create instance without running __init__; attach spies for batch_embedding and add_nodes
    DBClass = getattr(mod, "DSKnowledgeBase")
    inst = object.__new__(DBClass)

    calls = {"batch_embedding": [], "add_nodes": []}

    def batch_embedding(node_list):
        # record a shallow copy to preserve what was passed
        calls["batch_embedding"].append(list(node_list))

    def add_nodes(idea_node, neighbor_list):
        calls["add_nodes"].append((idea_node, list(neighbor_list)))

    # attach the spy methods
    inst.batch_embedding = batch_embedding
    inst.add_nodes = add_nodes

    return inst, calls


def test_add_idea_single_no_relations_round_081(reload_and_patch_module):
    """Single non-list input, no competition, no SCENARIO_PROBLEM, no FEEDBACK_PROBLEM.

    Expected behavior:
    - The code wraps the single idea into a one-item list branch (line ~65->66).
    - One IDEA node is created and passed to batch_embedding.
    - No add_nodes calls are made since add_pairs remains empty.
    """
    mod = reload_and_patch_module
    inst, calls = _make_db_instance(mod)

    idea = IdeaMock(idea="unique-idea", competition=None, hypothesis={}, name_str="IDE-1")

    # Call the method under test
    inst.add_idea(idea)

    # Assertions: batch_embedding called exactly once with a list that contains a single FakeNode
    assert len(calls["batch_embedding"]) == 1, "batch_embedding should be called once"
    node_list = calls["batch_embedding"][0]
    assert len(node_list) == 1
    only_node = node_list[0]
    assert only_node.content == "unique-idea"
    assert only_node.label == "IDEA"
    # appendix should be str(idea)
    assert only_node.appendix == str(idea)

    # No add_nodes calls expected
    assert calls["add_nodes"] == []


def test_add_idea_list_with_competition_and_sp_round_081(reload_and_patch_module):
    """List input path (line ~65->68) with competition and SCENARIO_PROBLEM present.

    Expected behavior:
    - idea_list is used directly (no wrapping)
    - Competition node and SCENARIO_PROBLEM node created and appended to node_list
    - add_nodes called once for each relationship created
    """
    mod = reload_and_patch_module
    inst, calls = _make_db_instance(mod)

    hypothesis = {"SCENARIO_PROBLEM": "scenario-A"}
    idea = IdeaMock(idea="idea-2", competition="comp-2", hypothesis=hypothesis, name_str="IDE-2")

    # Pass a list to hit the branch where isinstance(idea, list) is True
    inst.add_idea([idea])

    # Assertions
    assert len(calls["batch_embedding"]) == 1
    node_list = calls["batch_embedding"][0]

    # Should contain 3 nodes: idea node, competition node, SCENARIO_PROBLEM node
    contents = [(n.content, n.label) for n in node_list]
    assert ("idea-2", "IDEA") in contents
    assert ("comp-2", "competition") in contents
    assert ("scenario-A", "SCENARIO_PROBLEM") in contents

    # add_nodes should have been called for the competition relation and for the SP relation
    # In code order, competition relation is appended before SP relation
    assert len(calls["add_nodes"]) == 2

    # Verify first add_nodes call connects the IDEA node to the competition node
    first_call = calls["add_nodes"][0]
    idea_node_obj, neighbor_list = first_call
    assert idea_node_obj.label == "IDEA"
    assert neighbor_list and neighbor_list[0].label == "competition"

    # Verify second add_nodes call for SCENARIO_PROBLEM
    second_call = calls["add_nodes"][1]
    _, neighbor_list2 = second_call
    assert neighbor_list2 and neighbor_list2[0].label == "SCENARIO_PROBLEM"


def test_add_idea_both_sp_and_fp_round_081(reload_and_patch_module):
    """Idea with both SCENARIO_PROBLEM and FEEDBACK_PROBLEM present; no competition.

    Expected behavior:
    - Two problem nodes (SP and FP) are created and added to node_list
    - Two add_nodes calls are made for SP and FP in that order
    """
    mod = reload_and_patch_module
    inst, calls = _make_db_instance(mod)

    hypothesis = {"SCENARIO_PROBLEM": "scen-x", "FEEDBACK_PROBLEM": "feed-y"}
    idea = IdeaMock(idea="idea-3", competition=None, hypothesis=hypothesis, name_str="IDE-3")

    inst.add_idea(idea)

    # One batch_embedding call
    assert len(calls["batch_embedding"]) == 1
    node_list = calls["batch_embedding"][0]
    labels = [n.label for n in node_list]

    # Must include IDEA, SCENARIO_PROBLEM, FEEDBACK_PROBLEM
    assert "IDEA" in labels
    assert "SCENARIO_PROBLEM" in labels
    assert "FEEDBACK_PROBLEM" in labels

    # add_nodes called twice (SP then FP according to source order)
    assert len(calls["add_nodes"]) == 2
    sp_call = calls["add_nodes"][0]
    fp_call = calls["add_nodes"][1]

    assert sp_call[1][0].label == "SCENARIO_PROBLEM"
    assert fp_call[1][0].label == "FEEDBACK_PROBLEM"
