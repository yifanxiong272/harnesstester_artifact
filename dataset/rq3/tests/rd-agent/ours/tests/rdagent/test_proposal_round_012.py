import pytest

from rdagent.scenarios.kaggle.proposal import proposal as proposal_mod
from rdagent.scenarios.kaggle.proposal.proposal import generate_RAG_content


class Node:
    def __init__(self, content):
        self.content = content

    def __repr__(self):
        return f"Node({self.content!r})"

    def __eq__(self, other):
        return isinstance(other, Node) and self.content == other.content

    def __hash__(self):
        return hash(self.content)


class Doc:
    def __init__(self, content):
        self.content = content


class FakeVectorBase:
    def __init__(self, docs):
        self._docs = docs

    def search_experience(self, target, hypothesis_and_feedback, topk_k=5):
        # deterministic return: return up to topk_k docs
        return (self._docs[:topk_k], None)


class TemplateFake:
    def __init__(self, name):
        self.name = name

    def r(self, insights=None, experiences=None):
        # Return a plain dict so tests can inspect structure deterministically
        return {"template": self.name, "insights": insights, "experiences": experiences}


class FakeScenario:
    def __init__(self, if_using_vector_rag=False, mini_case=False, if_using_graph_rag=True, vector_base=None):
        self.if_using_vector_rag = if_using_vector_rag
        self.mini_case = mini_case
        self.if_using_graph_rag = if_using_graph_rag
        self.vector_base = vector_base

    def get_competition_full_desc(self):
        # used via trace.scen in generate_RAG_content; provide same text
        return "competition full desc"


class FakeTrace:
    def __init__(self, scen, knowledge_base):
        self.scen = scen
        self.knowledge_base = knowledge_base


class FakeKnowledgeBase:
    def __init__(self, same_comp_node, related_node, similar_node, found_nodes_map, nodes_for_experiments_and_conclusion):
        # found_nodes_map: mapping from (start_node, tuple(constraint_labels), steps) -> list[Node]
        self.same_comp_node = same_comp_node
        self.related_node = related_node
        self.similar_node = similar_node
        self.found_nodes_map = found_nodes_map
        self.nodes_for_experiments_and_conclusion = nodes_for_experiments_and_conclusion

    def get_node_by_content(self, content):
        # if content equals competition full desc -> same_comp_node, else None
        if content == "competition full desc":
            return self.same_comp_node
        return None

    def get_nodes_within_steps(self, start_node, steps, constraint_labels):
        key = (start_node, tuple(constraint_labels), steps)
        if key in self.found_nodes_map:
            return list(self.found_nodes_map[key])
        # fallback: check experiments/conclusion mapping by node identity
        if start_node in self.nodes_for_experiments_and_conclusion:
            mapping = self.nodes_for_experiments_and_conclusion[start_node]
            label = constraint_labels[0] if constraint_labels else None
            return mapping.get(label, [])
        return []

    def semantic_search(self, node, topk_k=2):
        # if called with chosen_hypothesis (string) or competition desc string, return the configured similar node
        return [self.similar_node]


@pytest.fixture(autouse=True)
def patch_module_globals(monkeypatch):
    # Ensure deterministic KG_ACTION_LIST and T template function for the tested module
    monkeypatch.setattr(proposal_mod, "KG_ACTION_LIST", ["act1"])  # small predictable list
    monkeypatch.setattr(proposal_mod, "T", lambda name: TemplateFake(name))
    yield


def test_vector_rag_mini_case_round_012():
    # vector rag path with mini_case True should call search_experience with topk_k=1 and return joined contents
    docs = [Doc("doc_one"), Doc("doc_two")]
    scen = FakeScenario(if_using_vector_rag=True, mini_case=True, vector_base=FakeVectorBase(docs))
    trace = FakeTrace(scen=scen, knowledge_base=None)

    result = generate_RAG_content(scen=scen, trace=trace, hypothesis_and_feedback="hb", target="tgt")

    assert result == "doc_one", "Expected single doc content when mini_case True and topk_k=1"


def test_graph_rag_no_chosen_hypothesis_round_012():
    # Build nodes
    same_comp = Node("competition full desc")
    related = Node("rel_hypo")
    similar = Node("sim_node")
    found1 = Node("found_longer_content")
    found2 = Node("f2")

    # mapping for get_nodes_within_steps
    # When starting from same_comp and constraint act1 -> return related node (for related_hypothesis_nodes)
    # When starting from similar and constraint act1 -> return found1 and related (so found_nodes includes a node that equals related)
    found_map = {
        (same_comp, tuple(["act1"]), 1): [related],
        (similar, tuple(["act1"]), 3): [found1, related],
        # for experiments/conclusion queries later, when start_node is found1 or found2 we will use nodes_for_experiments_and_conclusion
    }

    # experiments and conclusion mapping keyed by node
    exp_con_map = {
        # related node: leave empty -> triggers "No experiment information available."
        related: {},
        # found1: has both experiment and conclusion
        found1: {
            "experiments": [Node("found1_experiment")],
            "conclusion": [Node("found1_conclusion")],
        },
        # found2: only experiments available (simulate missing conclusion)
        found2: {
            "experiments": [Node("found2_experiment")],
            # no conclusion -> missing
        },
    }

    kb = FakeKnowledgeBase(same_comp_node=same_comp, related_node=related, similar_node=similar, found_nodes_map=found_map, nodes_for_experiments_and_conclusion=exp_con_map)
    scen = FakeScenario(if_using_vector_rag=False, if_using_graph_rag=True)
    trace = FakeTrace(scen=scen, knowledge_base=kb)

    # Call function with no chosen_hypothesis to exercise else branch building found_nodes from semantic_search
    result = generate_RAG_content(scen=scen, trace=trace, hypothesis_and_feedback="hb")

    # result should be dict returned by TemplateFake.r
    assert isinstance(result, dict)
    assert result["template"].startswith("scenarios.kaggle.prompts"), "Template name should be the expected prompt id"

    insights = result["insights"]
    experiences = result["experiences"]

    # experiences: should have at least the related hypothesis gathered earlier
    # related had no experiments -> should have message 'No experiment information available.' and no conclusion
    assert any(ex.get("hypothesis") == related.content for ex in experiences), "Related hypothesis should appear in experiences"
    rel_exp = [ex for ex in experiences if ex.get("hypothesis") == related.content][0]
    assert rel_exp.get("experiments") == "No experiment information available.", "Missing experiments branch must produce the default message"
    assert rel_exp.get("conclusion") == "No conclusion information available.", "Missing conclusion branch must produce the default message"

    # insights should include entries for found1 (since it had experiment and conclusion mapping)
    assert any(ins.get("experiments") == "found1_experiment" or ins.get("experiments") == "found2_experiment" or ins.get("experiments") == "found1_experiment" for ins in insights)


def test_graph_rag_with_chosen_hypothesis_round_012():
    # chosen_hypothesis path (lines 108-141)
    # Create nodes where semantic_search returns a similar node and get_nodes_within_steps returns hypothesis_nodes
    sim_node = Node("sim_for_choice")
    exp_node = Node("exp_node_content")
    # For convert loop: when searching hypothesis nodes from similar_node with chosen_hypothesis_type -> return exp_node
    found_map = {
        (sim_node, tuple(["chosen_type"]), 3): [exp_node],
        # When later asking for hypothesis nodes within steps from exp_node with KG_ACTION_LIST -> return no hypothesis (to hit 'No hypothesis information available.')
        (exp_node, tuple(proposal_mod.KG_ACTION_LIST), 2): [],
        # For conclusion search for exp_node, return empty to hit missing conclusion branch
        (exp_node, tuple(["conclusion"]), 2): [],
        # For experiments mapping inside insights, ask experiments for exp_node
        (exp_node, tuple(["experiments"]), 2): [Node("exp_node_experiment")],
    }

    kb = FakeKnowledgeBase(same_comp_node=None, related_node=None, similar_node=sim_node, found_nodes_map=found_map, nodes_for_experiments_and_conclusion={})
    scen = FakeScenario(if_using_vector_rag=False, if_using_graph_rag=True)
    trace = FakeTrace(scen=scen, knowledge_base=kb)

    result = generate_RAG_content(scen=scen, trace=trace, hypothesis_and_feedback="hb", chosen_hypothesis="choice_text", chosen_hypothesis_type="chosen_type")

    assert isinstance(result, dict)
    insights = result["insights"]

    # For the produced insight, hypothesis should be default missing message because hypothesis_node_list was empty
    assert any(ins.get("hypothesis") == "No hypothesis information available." for ins in insights), "When no hypothesis nodes found, default message must be present"
    # Conclusion missing -> should get default conclusion message
    assert any(ins.get("conclusion") == "No conclusion information available." for ins in insights), "Missing conclusions should lead to default conclusion message"
