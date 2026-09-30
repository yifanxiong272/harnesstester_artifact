import json
import types
import pytest

from rdagent.scenarios.data_science.proposal.exp_gen import idea_pool as ip


class FakeDSIdea:
    """Fake DSIdea used to capture creation and expose idea/method/context."""
    created = []

    def __init__(self, *, raw_knowledge):
        # raw_knowledge expected to be a dict with idea/method/context
        self.raw = raw_knowledge
        self.idea = raw_knowledge.get("idea", "idea_unknown")
        self.method = raw_knowledge.get("method", "method_unknown")
        self.context = raw_knowledge.get("context", "context_unknown")
        FakeDSIdea.created.append(self)

    def __str__(self):
        return f"{self.idea} - {self.method} - {self.context}"


class FakeT:
    def __init__(self, *_args, **_kwargs):
        pass

    def r(self, *args, **kwargs):
        # Return some harmless prompt representation
        return "PROMPT"


class FakeAPIBackend:
    # tests set this attribute to control the response
    response = "{}"

    def build_messages_and_create_chat_completion(
        self, user_prompt, system_prompt, json_mode, json_target_type
    ):
        # Always return the preconfigured JSON string
        return FakeAPIBackend.response


class FakeNode:
    def __init__(self, id, appendix=None, neighbors=None):
        self.id = id
        self.appendix = appendix
        self.neighbors = neighbors or []


class FakeSelf:
    def __init__(self, semantic_counts, idea_appendices_by_index, competition_node=None, used_idea_id_set=None):
        # semantic_counts: dict mapping problem_text -> number of sampled nodes
        # idea_appendices_by_index: dict mapping problem_text -> list of appendix dicts for idea nodes
        self.semantic_counts = semantic_counts
        self.idea_appendices_by_index = idea_appendices_by_index
        self._competition_node = competition_node
        self.used_idea_id_set = set(used_idea_id_set or [])

    def get_node_by_content(self, content):
        # Return the configured competition node or None
        return self._competition_node

    def semantic_search(self, node, constraint_labels=None):
        # node is the problem text; return list of indices representing sampled seeds
        n = self.semantic_counts.get(node, 0)
        return list(range(n))

    def get_nodes_within_steps(self, start_node, steps, constraint_labels=None):
        # start_node is an integer index (from semantic_search)
        # We produce an idea node whose appendix comes from idea_appendices_by_index
        # Map start_node index to the corresponding appendix by consuming in order
        # For uniqueness, create id as (1000 * problem_hash) + start_node not necessary; keep simple
        # We will rely on idea_appendices_by_index containing lists long enough
        # Identify the problem text by searching which problem maps to a list that contains enough indices
        for problem_text, appendices in self.idea_appendices_by_index.items():
            if start_node < len(appendices):
                appendix = appendices[start_node]
                node = FakeNode(id=appendix.get("_id", start_node), appendix=appendix, neighbors=appendix.get("neighbors", []))
                return [node]
        # default fallback
        node = FakeNode(id=start_node, appendix={"idea": f"idea_{start_node}", "method": "m", "context": "c"}, neighbors=[])
        return [node]


@pytest.fixture(autouse=True)
def patch_module(monkeypatch):
    # Patch DSIdea, T, and APIBackend in the module under test to avoid external dependencies.
    monkeypatch.setattr(ip, "DSIdea", FakeDSIdea)
    monkeypatch.setattr(ip, "T", FakeT)
    monkeypatch.setattr(ip, "APIBackend", FakeAPIBackend)


def test_update_happens_round_070(monkeypatch):
    # Problem 'prob' has 2 candidate ideas; API picks id 1 (1 < 2) so update should happen using index 0
    FakeDSIdea.created.clear()
    problem_text = "prob"

    semantic_counts = {problem_text: 2}
    # Prepare two appendix dicts for two idea nodes; include explicit _id
    appendix0 = {"idea": "IdeaA", "method": "M1", "context": "C1", "_id": 10}
    appendix1 = {"idea": "IdeaB", "method": "M2", "context": "C2", "_id": 11}
    idea_appendices_by_index = {problem_text: [appendix0, appendix1]}

    fake_self = FakeSelf(semantic_counts=semantic_counts, idea_appendices_by_index=idea_appendices_by_index, competition_node=None)

    problems = {"prob": {"problem": problem_text, "label": "L"}}

    # API returns picked_id 1 -> since len==2, 1 < 2 True -> index used = picked_id - 1 = 0
    FakeAPIBackend.response = json.dumps({"prob": 1})

    # Call the method under test
    res = ip.DSKnowledgeBase.sample_ideas(fake_self, problems, "sdesc", "fdesc", "sotad", "compd")

    # Expect the problem to be updated with idea and idea_node_id from appendix0
    assert "idea" in res["prob"] and "idea_node_id" in res["prob"]
    assert res["prob"]["idea"] == appendix0
    assert res["prob"]["idea_node_id"] == 10

    # DSIdea should have been constructed for the appended idea(s)
    assert len(FakeDSIdea.created) >= 1
    created = FakeDSIdea.created[0]
    assert created.idea == "IdeaA" and created.method == "M1" and created.context == "C1"


def test_no_update_when_picked_out_of_range_round_070(monkeypatch):
    # Problem 'single' has 1 candidate; API returns picked_id 1 -> 1 < 1 is False -> no update
    FakeDSIdea.created.clear()
    problem_text = "single"
    semantic_counts = {problem_text: 1}
    appendix0 = {"idea": "OnlyIdea", "method": "M", "context": "C", "_id": 5}
    idea_appendices_by_index = {problem_text: [appendix0]}

    fake_self = FakeSelf(semantic_counts=semantic_counts, idea_appendices_by_index=idea_appendices_by_index, competition_node=None)
    problems = {"single": {"problem": problem_text, "label": "L"}}

    FakeAPIBackend.response = json.dumps({"single": 1})

    res = ip.DSKnowledgeBase.sample_ideas(fake_self, problems, "sdesc", "fdesc", "sotad", "compd")

    # Because picked_id == len(list) no update should be performed
    assert "idea" not in res["single"]
    assert "idea_node_id" not in res["single"]

    # But DSIdea shouldn't have been created because we never appended an idea (the if guarded creation)
    # Ensure either zero or at most one (in other flows) but here should be zero
    assert len(FakeDSIdea.created) == 0


def test_competition_and_used_skip_round_070(monkeypatch):
    # When competition node is present in idea_node.neighbors or idea id is in used_idea_id_set,
    # the candidate should be skipped and not appended
    FakeDSIdea.created.clear()
    problem_text = "prob_comp"
    semantic_counts = {problem_text: 2}

    # Create a single competition node object and ensure idea nodes reference it in neighbors
    competition_node = object()
    appendix0 = {"idea": "I1", "method": "m1", "context": "c1", "_id": 21, "neighbors": [competition_node]}
    appendix1 = {"idea": "I2", "method": "m2", "context": "c2", "_id": 22, "neighbors": []}
    idea_appendices_by_index = {problem_text: [appendix0, appendix1]}

    # Make used_idea_id_set include the second id so both are excluded (one by competition, one by used set)
    used = {22}
    fake_self = FakeSelf(semantic_counts=semantic_counts, idea_appendices_by_index=idea_appendices_by_index, competition_node=competition_node, used_idea_id_set=used)

    problems = {"prob_comp": {"problem": problem_text, "label": "L"}}

    FakeAPIBackend.response = json.dumps({"prob_comp": 0})

    res = ip.DSKnowledgeBase.sample_ideas(fake_self, problems, "sdesc", "fdesc", "sotad", "compd")

    # No candidate appended -> no update
    assert "idea" not in res["prob_comp"]

    # No DSIdea created
    assert len(FakeDSIdea.created) == 0


def test_break_at_five_candidates_round_070(monkeypatch):
    # Ensure that when many candidates exist we only append up to 5 and then break
    FakeDSIdea.created.clear()
    problem_text = "many"
    # Provide 6 candidates to trigger the break when count reaches 5
    semantic_counts = {problem_text: 6}
    appendices = []
    for i in range(6):
        appendices.append({"idea": f"I{i}", "method": "m{i}", "context": f"c{i}", "_id": 300 + i})
    idea_appendices_by_index = {problem_text: appendices}
    fake_self = FakeSelf(semantic_counts=semantic_counts, idea_appendices_by_index=idea_appendices_by_index, competition_node=None, used_idea_id_set=set())

    problems = {"many": {"problem": problem_text, "label": "L"}}

    # API response irrelevant; set to a value that would otherwise select something
    FakeAPIBackend.response = json.dumps({"many": 2})

    res = ip.DSKnowledgeBase.sample_ideas(fake_self, problems, "sdesc", "fdesc", "sotad", "compd")

    # We cannot directly access the internal list, but DSIdea.created reflects how many were instantiated
    # DSIdea is constructed exactly when an idea is appended inside the method, so we expect 5 creations
    assert len(FakeDSIdea.created) == 5
