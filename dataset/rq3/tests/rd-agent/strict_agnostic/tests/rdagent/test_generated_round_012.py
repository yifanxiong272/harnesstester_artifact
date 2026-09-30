import json
import pytest

# Import the module under test. We import the module object to monkeypatch module-level
# constants like KG_ACTION_LIST and T, and import the function under test.
import rdagent.scenarios.kaggle.proposal.proposal as proposal_mod
from rdagent.scenarios.kaggle.proposal.proposal import generate_RAG_content


class FakeDoc:
    def __init__(self, content):
        self.content = content


class FakeNode:
    def __init__(self, content):
        self.content = content

    def __repr__(self):
        return f"FakeNode({self.content!r})"

    def __eq__(self, other):
        return isinstance(other, FakeNode) and self.content == other.content

    def __hash__(self):
        return hash(self.content)


class FakeVectorBase:
    def __init__(self, prefix="VEC"):
        self.prefix = prefix

    def search_experience(self, target, hypothesis_and_feedback, topk_k=1):
        # Deterministic: return one FakeDoc whose content encodes the parameters
        docs = [FakeDoc(f"{self.prefix}:k={topk_k}:t={target}:fb={hypothesis_and_feedback}")]
        return docs, None


class FakeKB:
    def __init__(self, same_comp_node=None):
        # same_comp_node: FakeNode or None
        self._same_comp_node = same_comp_node

    def get_node_by_content(self, content):
        # Return the preset same_comp_node regardless of content for predictability when set
        return self._same_comp_node

    def get_nodes_within_steps(self, start_node, steps, constraint_labels=None):
        # Deterministic behavior based on the constraint label and start_node content so tests
        # can exercise different branches.
        label = None
        if constraint_labels:
            # constraint_labels is expected to be a list
            label = constraint_labels[0]

        # If called to discover hypothesis nodes from the competition node
        if start_node is self._same_comp_node and label is not None:
            # For hypothesis discovery from same competition node, return a node named H_<label>
            return [FakeNode(f"H_{label}")]

        # If asked for 'experiments' or 'conclusion' for a hypothesis start node,
        # return content that encodes whether the node has information.
        if label == "experiments":
            # Return an experiment for nodes that have 'H_' prefix, otherwise empty
            if start_node.content.startswith("H_"):
                return [FakeNode(f"exp_for_{start_node.content}")]
            return []

        if label == "conclusion":
            # Return a conclusion only for specific nodes to exercise both branches
            if start_node.content.endswith("a2") or start_node.content.endswith("_a2"):
                return [FakeNode(f"concl_for_{start_node.content}")]
            return []

        # When called from the found 'exp' or 'hypothesis' exploration (longer steps),
        # return a hypothesis or experiment node based on the start_node name
        # If constraint_labels corresponds to any hypothesis action list element, return a derived node
        if label is not None and label.startswith("H_"):
            return [FakeNode(f"derived_{start_node.content}_{label}")]

        # Fallback: empty list
        return []

    def semantic_search(self, node, topk_k=2):
        # Deterministic set of similar nodes based on the node string
        # If node looks like a chosen hypothesis (string), return nodes that will be used
        return [FakeNode("simA"), FakeNode("simB")][:topk_k]


class FakeTemplate:
    def __init__(self, path):
        self.path = path

    def r(self, insights, experiences):
        # Deterministic rendering: JSON with sorted keys for stable comparisons
        return json.dumps({"insights": insights, "experiences": experiences}, sort_keys=True)


def make_trace_with_kb(same_comp_node=None):
    class Trace:
        pass

    trace = Trace()
    trace.knowledge_base = FakeKB(same_comp_node=same_comp_node)
    # trace.scen is used later when chosen_hypothesis is None
    class SceneLike:
        def get_competition_full_desc(self):
            return "competition_full_desc"

    trace.scen = SceneLike()
    return trace


def make_scen_vector(mini_case=True, prefix="VEC"):
    class Scen:
        pass

    scen = Scen()
    scen.if_using_vector_rag = True
    scen.mini_case = mini_case
    scen.vector_base = FakeVectorBase(prefix=prefix)
    return scen


def make_scen_graph(if_using_graph_rag=True, same_comp=True):
    class Scen:
        def get_competition_full_desc(self):
            return "competition_full_desc"

    scen = Scen()
    scen.if_using_vector_rag = False
    scen.if_using_graph_rag = if_using_graph_rag
    scen.get_competition_full_desc = scen.get_competition_full_desc
    # scen is also referenced via trace.scen in generate_RAG_content
    return scen


def test_vector_mini_round_012(monkeypatch):
    """Covers vector RAG branch when mini_case is True (topk_k=1)."""
    monkeypatch.setattr(proposal_mod, "T", FakeTemplate)
    # small deterministic vector base
    scen = make_scen_vector(mini_case=True, prefix="MINI_VEC")
    trace = make_trace_with_kb(same_comp_node=None)

    out = generate_RAG_content(scen, trace, hypothesis_and_feedback="feedback1", target="TGT")
    # Expect the single document content produced by FakeVectorBase.joined by newline (single element)
    expected_doc = f"MINI_VEC:k=1:t=TGT:fb=feedback1"
    assert out == expected_doc


def test_vector_full_round_012(monkeypatch):
    """Covers vector RAG branch when mini_case is False (topk_k=5).
    Our FakeVectorBase still returns a single doc that encodes k=5 so we can assert deterministically.
    """
    monkeypatch.setattr(proposal_mod, "T", FakeTemplate)
    scen = make_scen_vector(mini_case=False, prefix="FULL_VEC")
    trace = make_trace_with_kb(same_comp_node=None)

    out = generate_RAG_content(scen, trace, hypothesis_and_feedback="feedback2", target="T")
    expected_doc = f"FULL_VEC:k=5:t=T:fb=feedback2"
    assert out == expected_doc


def test_graph_rag_insights_and_experiences_round_012(monkeypatch):
    """Covers graph RAG branches: related hypothesis discovery, experiences building,
    semantic search for similar nodes, found_nodes processing, and default fallbacks for
    missing experiments/conclusions. The Template T is monkeypatched to a deterministic renderer.
    """
    # Monkeypatch the template renderer to a deterministic function
    monkeypatch.setattr(proposal_mod, "T", FakeTemplate)

    # Ensure KG_ACTION_LIST is a deterministic small list for the test
    monkeypatch.setattr(proposal_mod, "KG_ACTION_LIST", ["a1", "a2"])  # two actions

    # Prepare a same_comp_node so that related_hypothesis_nodes is non-empty
    same_comp_node = FakeNode("COMP")
    trace = make_trace_with_kb(same_comp_node=same_comp_node)

    # The scen returned by trace.scen is used for competition description when chosen_hypothesis is None
    scen = make_scen_graph(if_using_graph_rag=True, same_comp=True)

    # The FakeKB.get_nodes_within_steps is designed to return H_<label> for competition node, giving
    # related_hypothesis_nodes = [H_a1, H_a2]
    # semantic_search returns [simA, simB]; for each similar_node and each hypothesis_type in KG_ACTION_LIST,
    # get_nodes_within_steps returns [FakeNode(f"H_{label}")] for that label; therefore found_nodes will
    # include H_a1 and H_a2 (matching related_hypothesis_nodes) and duplicates are deduped via set.
    # For H_a1 (which matches related_hypothesis_nodes), when iterating insights building we will hit the
    # "continue" branch and skip it. For others, experiments/conclusions may or may not be present
    # (FakeKB returns experiments for nodes with 'H_' prefix and conclusions only for names ending with '_a2').

    out = generate_RAG_content(scen, trace, hypothesis_and_feedback="irrelevant", target=None)

    # The FakeTemplate serializes a dict with keys 'insights' and 'experiences'. Load it and assert
    # structure and presence of expected keys and messages.
    parsed = json.loads(out)
    assert isinstance(parsed, dict)
    assert "insights" in parsed and "experiences" in parsed

    # experiences should be built from related_hypothesis_nodes H_a1 and H_a2 deterministically
    exps = parsed["experiences"]
    # There should be one experience entry per related hypothesis node
    assert any(e.get("hypothesis", "").startswith("H_") for e in exps)

    # For each experience, experiments should be present (FakeKB returns experiments for H_*)
    for e in exps:
        assert "experiments" in e
        # conclusion may be present only for ones matching a2 rule; otherwise default message
        if e["hypothesis"].endswith("a2") or e["hypothesis"].endswith("_a2"):
            assert not e["conclusion"].startswith("No conclusion"), "expected a concrete conclusion"
        else:
            # Other nodes get the default conclusion text when none provided
            assert e["conclusion"] == "No conclusion information available." or e["conclusion"].startswith("concl_for_")

    # Insights list should be present and be a list
    insights = parsed["insights"]
    assert isinstance(insights, list)
    # Each insight must have hypothesis/experiments/conclusion keys or default messages
    for ins in insights:
        assert "hypothesis" in ins or "experiments" in ins
        # experiments or default
        assert "experiments" in ins
        assert "conclusion" in ins
