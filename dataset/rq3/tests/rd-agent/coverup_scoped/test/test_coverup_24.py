# file: rdagent/scenarios/data_science/proposal/exp_gen/idea_pool.py:116-180
# asked: {"lines": [125, 126, 127, 129, 130, 131, 134, 135, 136, 137, 138, 140, 141, 143, 144, 145, 146, 147, 148, 149, 150, 151, 154, 155, 156, 158, 159, 160, 161, 162, 164, 165, 166, 167, 168, 170, 173, 174, 175, 177, 178, 180], "branches": [[129, 130], [129, 154], [137, 138], [137, 151], [140, 143], [140, 149], [149, 137], [149, 150], [173, 174], [173, 180], [174, 173], [174, 177]]}
# gained: {"lines": [125, 126, 127, 129, 130, 131, 134, 135, 136, 137, 138, 140, 141, 143, 144, 145, 146, 147, 148, 149, 151, 154, 155, 156, 158, 159, 160, 161, 162, 164, 165, 166, 167, 168, 170, 173, 174, 175, 177, 178, 180], "branches": [[129, 130], [129, 154], [137, 138], [137, 151], [140, 143], [140, 149], [149, 137], [173, 174], [173, 180], [174, 173], [174, 177]]}

import json
import types
import pytest

import rdagent.scenarios.data_science.proposal.exp_gen.idea_pool as idea_pool_module


class FakeNode:
    def __init__(self, id, appendix, neighbors=None):
        self.id = id
        self.appendix = appendix
        self.neighbors = set(neighbors) if neighbors is not None else set()

    def __repr__(self):
        return f"FakeNode(id={self.id})"


class FakeT:
    def __init__(self, *_):
        pass

    def r(self, *args, **kwargs):
        # return a simple string prompt
        return "PROMPT"


class FakeAPIBackend:
    def __init__(self, response_str):
        self._response = response_str

    def build_messages_and_create_chat_completion(
        self,
        user_prompt=None,
        system_prompt=None,
        json_mode=None,
        json_target_type=None,
    ):
        return self._response


def make_appendix(idea_label):
    return {
        "idea": idea_label,
        "method": f"method_for_{idea_label}",
        "context": f"context_for_{idea_label}",
        "hypothesis": {"scenario_problem": "sp", "feedback_problem": "fp"},
    }


def call_sample_ideas_with_mocks(monkeypatch, *,
                                 problems,
                                 semantic_search_map,
                                 get_nodes_map,
                                 competition_node=None,
                                 api_response_dict=None,
                                 used_idea_id_set=None):
    monkeypatch.setattr(idea_pool_module, "T", FakeT)
    response_str = json.dumps(api_response_dict or {})
    monkeypatch.setattr(idea_pool_module, "APIBackend", lambda: FakeAPIBackend(response_str))

    fake_self = types.SimpleNamespace()
    fake_self.used_idea_id_set = set(used_idea_id_set or set())

    def fake_get_node_by_content(content):
        return competition_node

    def fake_semantic_search(node, constraint_labels=None):
        return list(semantic_search_map.get(node, []))

    def fake_get_nodes_within_steps(start_node, steps=1, constraint_labels=None):
        return list(get_nodes_map.get(start_node, []))

    fake_self.get_node_by_content = fake_get_node_by_content
    fake_self.semantic_search = fake_semantic_search
    fake_self.get_nodes_within_steps = fake_get_nodes_within_steps

    result = idea_pool_module.DSKnowledgeBase.sample_ideas(
        fake_self,
        problems,
        scenario_desc="scenario",
        exp_feedback_list_desc="feedbacks",
        sota_exp_desc="sota",
        competition_desc="competition search",
    )
    return result


def test_sample_ideas_selects_and_updates_problems(monkeypatch):
    problems = {
        "ProbA": {"problem": "probA description", "label": "L"},
        "ProbB": {"problem": "probB description", "label": "L"},
    }

    start_A1, start_A2 = "startA1", "startA2"
    start_B1, start_B2 = "startB1", "startB2"

    idea_A1 = FakeNode("aid1", make_appendix("IdeaA1"))
    idea_A2 = FakeNode("aid2", make_appendix("IdeaA2"))
    idea_B1 = FakeNode("bid1", make_appendix("IdeaB1"))
    idea_B2 = FakeNode("bid2", make_appendix("IdeaB2"))

    semantic_map = {
        "probA description": [start_A1, start_A2],
        "probB description": [start_B1, start_B2],
    }

    get_nodes_map = {
        start_A1: [idea_A1],
        start_A2: [idea_A2],
        start_B1: [idea_B1],
        start_B2: [idea_B2],
    }

    # Use picks that satisfy the code's strict '<' check (picked_id < len(list))
    api_response = {"ProbA": 1, "ProbB": 1}

    res = call_sample_ideas_with_mocks(
        monkeypatch,
        problems=problems,
        semantic_search_map=semantic_map,
        get_nodes_map=get_nodes_map,
        competition_node=None,
        api_response_dict=api_response,
        used_idea_id_set=set(),
    )

    assert "idea" in res["ProbA"]
    assert res["ProbA"]["idea"]["idea"] == "IdeaA1"
    assert res["ProbA"]["idea_node_id"] == "aid1"

    assert "idea" in res["ProbB"]
    assert res["ProbB"]["idea"]["idea"] == "IdeaB1"
    assert res["ProbB"]["idea_node_id"] == "bid1"


def test_sample_ideas_skips_used_or_competing_and_handles_invalid_pick(monkeypatch):
    problems = {
        "ProbX": {"problem": "probX description", "label": "L"},
    }

    start_x1, start_x2 = "startX1", "startX2"
    competition_node = object()
    idea_x1 = FakeNode("xid1", make_appendix("IdeaX1"), neighbors={competition_node})
    idea_x2 = FakeNode("xid2", make_appendix("IdeaX2"), neighbors={competition_node})

    semantic_map = {"probX description": [start_x1, start_x2]}
    get_nodes_map = {start_x1: [idea_x1], start_x2: [idea_x2]}

    used_ids = {"xid1"}

    api_response = {"ProbX": 1}

    res = call_sample_ideas_with_mocks(
        monkeypatch,
        problems=problems,
        semantic_search_map=semantic_map,
        get_nodes_map=get_nodes_map,
        competition_node=competition_node,
        api_response_dict=api_response,
        used_idea_id_set=used_ids,
    )

    assert "idea" not in res["ProbX"]
    assert "idea_node_id" not in res["ProbX"]
