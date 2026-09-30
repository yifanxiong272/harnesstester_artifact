# file: rdagent/scenarios/kaggle/proposal/proposal.py:58-182
# asked: {"lines": [66, 67, 68, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 86, 87, 88, 89, 90, 91, 93, 94, 96, 97, 98, 100, 101, 103, 104, 106, 107, 108, 109, 110, 111, 114, 115, 116, 117, 118, 120, 122, 124, 125, 126, 127, 129, 130, 132, 133, 134, 136, 137, 139, 140, 142, 143, 144, 147, 148, 149, 150, 151, 152, 154, 156, 158, 159, 160, 161, 162, 163, 165, 166, 168, 169, 170, 172, 173, 175, 176, 178, 179, 180, 182], "branches": [[66, 67], [66, 72], [67, 68], [67, 70], [72, 73], [72, 74], [75, 76], [75, 86], [77, 78], [77, 87], [88, 89], [88, 106], [93, 94], [93, 96], [100, 101], [100, 103], [108, 109], [108, 142], [114, 115], [114, 122], [124, 125], [124, 178], [129, 130], [129, 132], [136, 137], [136, 139], [147, 148], [147, 156], [148, 147], [148, 149], [158, 159], [158, 178], [159, 160], [159, 161], [165, 166], [165, 168], [172, 173], [172, 175]]}
# gained: {"lines": [66, 67, 68, 70, 71, 72, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 87, 88, 89, 90, 91, 93, 94, 96, 97, 98, 100, 101, 103, 104, 106, 107, 108, 109, 110, 111, 114, 115, 116, 117, 118, 120, 122, 124, 142, 143, 144, 147, 148, 149, 150, 151, 152, 154, 156, 158, 178, 179, 180, 182], "branches": [[66, 67], [66, 72], [67, 68], [67, 70], [72, 74], [75, 76], [77, 78], [77, 87], [88, 89], [88, 106], [93, 94], [93, 96], [100, 101], [100, 103], [108, 109], [108, 142], [114, 115], [114, 122], [124, 178], [147, 148], [147, 156], [148, 147], [148, 149], [158, 178]]}

import types
import pytest

from rdagent.scenarios.kaggle.proposal.proposal import generate_RAG_content
from rdagent.scenarios.kaggle.experiment.scenario import KG_ACTION_LIST
import rdagent.scenarios.kaggle.proposal.proposal as proposal_module


class Node:
    def __init__(self, content):
        self.content = content

    def __repr__(self):
        return f"Node({self.content!r})"

    def __eq__(self, other):
        return isinstance(other, Node) and self.content == other.content

    def __hash__(self):
        return hash(self.content)


class VectorBaseStub:
    def __init__(self):
        self.calls = []

    def search_experience(self, target, hypothesis_and_feedback, topk_k=5):
        # record call for assertions
        self.calls.append({"target": target, "hypothesis_and_feedback": hypothesis_and_feedback, "topk_k": topk_k})
        # return docs with content
        docs = [types.SimpleNamespace(content=f"doc_{i}_{topk_k}") for i in range(topk_k)]
        return docs, None


class KGScenarioStub:
    def __init__(self, if_using_vector_rag=False, mini_case=False, if_using_graph_rag=True):
        self.if_using_vector_rag = if_using_vector_rag
        self.mini_case = mini_case
        self.if_using_graph_rag = if_using_graph_rag
        self.vector_base = VectorBaseStub()

    def get_competition_full_desc(self):
        return "COMP_FULL_DESC"


class TraceStub:
    def __init__(self, scen, knowledge_base):
        self.scen = scen
        self.knowledge_base = knowledge_base


class KnowledgeBaseStub:
    def __init__(self, scen):
        # prepare nodes
        self.scen = scen
        self.same_comp_node = Node(scen.get_competition_full_desc())
        # create hypothesis nodes per action
        self.hypothesis_nodes = {action: Node(f"HYP_{action}") for action in KG_ACTION_LIST}
        # for some hypothesis nodes, create experiment and conclusion nodes
        self.experiments = {action: Node(f"EXP_{action}") for action in KG_ACTION_LIST}
        self.conclusions = {action: Node(f"CONCL_{action}") for action in KG_ACTION_LIST}

    def get_node_by_content(self, content):
        if content == self.same_comp_node.content:
            return self.same_comp_node
        return None

    def get_nodes_within_steps(self, start_node, steps, constraint_labels):
        # When start is same_comp_node and constraint_labels contains an action, return corresponding hypothesis node
        if start_node == self.same_comp_node:
            label = constraint_labels[0] if constraint_labels else None
            if label in self.hypothesis_nodes:
                return [self.hypothesis_nodes[label]]
            return []
        # When start_node is a hypothesis node and asking for experiments or conclusion (steps 1)
        for action, hyp in self.hypothesis_nodes.items():
            if start_node == hyp:
                label = constraint_labels[0] if constraint_labels else None
                if label == "experiments":
                    # For one action return no experiments to test branch
                    if action.endswith(KG_ACTION_LIST[0]):
                        return [self.experiments[action]]
                    return []
                if label == "conclusion":
                    # For one action return none to test branch
                    if action.endswith(KG_ACTION_LIST[1]):
                        return [self.conclusions[action]]
                    return []
        # When start_node is an experiment node and asked for hypothesis or conclusion (steps 2)
        for action, exp in self.experiments.items():
            if start_node == exp:
                label = constraint_labels
                # if looking for KG_ACTION_LIST (hypotheses), return associated hypothesis node for one case
                if label == KG_ACTION_LIST:
                    # return hypothesis node for first action to test hypothesis present branch
                    return [self.hypothesis_nodes[KG_ACTION_LIST[0]]]
                if label == ["conclusion"]:
                    return [self.conclusions[action]] if action.endswith(KG_ACTION_LIST[0]) else []
        # When looking for experiments or conclusion starting from hypothesis in the insights-other branch (steps 2)
        for action, hyp in self.hypothesis_nodes.items():
            if start_node == hyp:
                label = constraint_labels[0] if constraint_labels else None
                if label == "experiments":
                    return [self.experiments[action]] if action.endswith(KG_ACTION_LIST[0]) else []
                if label == "conclusion":
                    return [self.conclusions[action]] if action.endswith(KG_ACTION_LIST[1]) else []
        return []

    def semantic_search(self, node, topk_k=2):
        # If node is a chosen hypothesis string, return experiment nodes to go into chosen_hypothesis branch
        if isinstance(node, str) and node == "chosen_hypothesis_text":
            # return experiment nodes (simulate similar experiment nodes)
            return [self.experiments[KG_ACTION_LIST[0]], self.experiments[KG_ACTION_LIST[1]]][:topk_k]
        # If searching by competition full desc, return hypothesis nodes as similar nodes
        if node == self.scen.get_competition_full_desc():
            return [self.hypothesis_nodes[KG_ACTION_LIST[0]], self.hypothesis_nodes[KG_ACTION_LIST[1]]][:topk_k]
        return []


class TStub:
    def __init__(self, template_name):
        self.template_name = template_name
        self.called = False

    def r(self, insights=None, experiences=None):
        self.called = True
        # return repr string so tests can assert presence of expected pieces
        return f"TEMPLATE:{self.template_name}|INSIGHTS:{insights}|EXPERIENCES:{experiences}"


def test_generate_RAG_content_vector_rag_mini_and_full(monkeypatch):
    # Test both mini_case True and False to hit both topk_k branches
    scen_mini = KGScenarioStub(if_using_vector_rag=True, mini_case=True)
    scen_full = KGScenarioStub(if_using_vector_rag=True, mini_case=False)

    # patch T to avoid template dependency
    monkeypatch.setattr(proposal_module, "T", TStub)

    # call for mini_case (topk_k=1)
    res_mini = generate_RAG_content(scen=scen_mini, trace=None, hypothesis_and_feedback="hb", target="targ")
    # expect one doc content (doc_0_1)
    assert "doc_0_1" in res_mini
    assert scen_mini.vector_base.calls and scen_mini.vector_base.calls[-1]["topk_k"] == 1

    # call for full (topk_k=5)
    res_full = generate_RAG_content(scen=scen_full, trace=None, hypothesis_and_feedback="hb2", target=None)
    # expect five docs joined
    for i in range(5):
        assert f"doc_{i}_5" in res_full
    assert scen_full.vector_base.calls and scen_full.vector_base.calls[-1]["topk_k"] == 5


def test_generate_RAG_content_graph_rag_branches(monkeypatch):
    # Prepare scenario and knowledge base
    scen = KGScenarioStub(if_using_vector_rag=False, mini_case=False, if_using_graph_rag=True)
    kb = KnowledgeBaseStub(scen)
    trace = TraceStub(scen=scen, knowledge_base=kb)

    # Patch T used inside the module so RAG_content generation is deterministic
    monkeypatch.setattr(proposal_module, "T", TStub)

    # Case A: chosen_hypothesis provided -> goes into chosen_hypothesis branch
    rag_a = generate_RAG_content(scen=scen, trace=trace, hypothesis_and_feedback="hf", chosen_hypothesis="chosen_hypothesis_text", chosen_hypothesis_type=KG_ACTION_LIST[0])
    assert isinstance(rag_a, str)
    # The template stub outputs insights and experiences; since we have related_hypothesis_nodes from same_comp_node,
    # experiences should include hypothesis entries (from related_hypothesis_nodes)
    assert "EXPERIENCES" in rag_a
    assert "INSIGHTS" in rag_a
    # Ensure that the chosen_hypothesis semantic_search branch was exercised by presence of known experiment node in insights
    assert "EXP_" in rag_a

    # Case B: chosen_hypothesis is None -> goes into alternative branch
    rag_b = generate_RAG_content(scen=scen, trace=trace, hypothesis_and_feedback="hf", chosen_hypothesis=None)
    assert isinstance(rag_b, str)
    # Ensure template was called and contains expected keys
    assert "TEMPLATE:scenarios.kaggle.prompts:KG_hypothesis_gen_RAG" in rag_b
    # experiences and insights segments must exist (even if empty lists)
    assert "|INSIGHTS:" in rag_b and "|EXPERIENCES:" in rag_b
