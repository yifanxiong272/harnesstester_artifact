# file: rdagent/scenarios/data_science/proposal/exp_gen/idea_pool.py:116-180
# asked: {"lines": [125, 126, 127, 129, 130, 131, 134, 135, 136, 137, 138, 140, 141, 143, 144, 145, 146, 147, 148, 149, 150, 151, 154, 155, 156, 158, 159, 160, 161, 162, 164, 165, 166, 167, 168, 170, 173, 174, 175, 177, 178, 180], "branches": [[129, 130], [129, 154], [137, 138], [137, 151], [140, 143], [140, 149], [149, 137], [149, 150], [173, 174], [173, 180], [174, 173], [174, 177]]}
# gained: {"lines": [125, 126, 127, 129, 130, 131, 134, 135, 136, 137, 138, 140, 141, 143, 144, 145, 146, 147, 148, 149, 151, 154, 155, 156, 158, 159, 160, 161, 162, 164, 165, 166, 167, 168, 170, 173, 174, 175, 177, 178, 180], "branches": [[129, 130], [129, 154], [137, 138], [137, 151], [140, 143], [140, 149], [149, 137], [173, 174], [173, 180], [174, 177]]}

import json
import pytest

import rdagent.scenarios.data_science.proposal.exp_gen.idea_pool as idea_pool_mod


class FakeNode:
    def __init__(self, id_, appendix="", neighbors=None):
        self.id = id_
        self.appendix = appendix
        self.neighbors = neighbors or []

    def __repr__(self):
        return f"<FakeNode id={self.id} appendix={self.appendix} neighbors={self.neighbors}>"


class FakeDSIdea:
    def __init__(self, raw_knowledge):
        # raw_knowledge is expected to be a string; populate idea/method/context for text assembly
        self.idea = f"IdeaFrom:{raw_knowledge}"
        self.method = f"MethodFrom:{raw_knowledge}"
        self.context = f"ContextFrom:{raw_knowledge}"


class FakeT:
    def __init__(self, arg=None):
        self.arg = arg

    def r(self, **kwargs):
        # Return a simple predictable string; include problem_ideas if present for coverage
        if "problem_ideas" in kwargs:
            return f"user_prompt_with:{kwargs['problem_ideas']}"
        return f"system_prompt_for:{self.arg}"


class FakeAPIBackend:
    def __init__(self, response_text):
        # response_text should be a JSON string to mimic the real backend
        self._response_text = response_text
        self.called = False
        self.call_args = None

    def build_messages_and_create_chat_completion(self, user_prompt, system_prompt, json_mode, json_target_type):
        self.called = True
        self.call_args = dict(user_prompt=user_prompt, system_prompt=system_prompt, json_mode=json_mode, json_target_type=json_target_type)
        return self._response_text


def make_instance_without_init():
    # create DSKnowledgeBase instance without calling __init__ to avoid side effects
    inst = object.__new__(idea_pool_mod.DSKnowledgeBase)
    return inst


def setup_common_monkeypatches(monkeypatch, api_response_json):
    # Patch DSIdea, T, and APIBackend in the module to controlled fakes
    monkeypatch.setattr(idea_pool_mod, "DSIdea", FakeDSIdea)
    monkeypatch.setattr(idea_pool_mod, "T", FakeT)
    fake_api = FakeAPIBackend(api_response_json)
    monkeypatch.setattr(idea_pool_mod, "APIBackend", lambda: fake_api)
    return fake_api


def test_sample_ideas_basic_selection(monkeypatch):
    """
    Test that sample_ideas collects idea nodes correctly when there is no competition node,
    excludes used idea ids, and updates the problems dict according to APIBackend response.
    """
    # Prepare fake API response:
    # For prob1: 1 selects first among two items (picked_id < len -> 1 < 2 True -> index 0)
    # For prob2: 0 selects the only item (picked_id < len -> 0 < 1 True -> index -1 -> last)
    response = json.dumps({"prob1": 1, "prob2": 0})
    fake_api = setup_common_monkeypatches(monkeypatch, response)

    inst = make_instance_without_init()
    # used_idea_id_set empty initially
    inst.used_idea_id_set = set()

    # Create idea nodes (these are returned by get_nodes_within_steps)
    idea10 = FakeNode(10, appendix="appendix10", neighbors=[])
    idea11 = FakeNode(11, appendix="appendix11", neighbors=[])
    idea12 = FakeNode(12, appendix="appendix12", neighbors=[])
    idea13 = FakeNode(13, appendix="appendix13", neighbors=[])

    # Map start nodes to idea nodes via get_nodes_within_steps
    start_to_idea = {
        "s1": idea10,
        "s2": idea11,
        "s3": idea12,
        "s4": idea13,
    }

    # semantic_search should return a list of 'start' nodes, represented simply by strings here
    def fake_semantic_search(node, constraint_labels):
        # distinguish by node value passed in problems
        return {
            "p1_start": ["s1", "s2"],
            "p2_start": ["s3", "s4"],
        }[node]

    def fake_get_nodes_within_steps(start_node, steps, constraint_labels):
        # return a list where first element is the idea node corresponding to start_node
        return [start_to_idea[start_node]]

    # No competition node
    def fake_get_node_by_content(content):
        return None

    # Attach fake methods to instance
    inst.semantic_search = fake_semantic_search
    inst.get_nodes_within_steps = fake_get_nodes_within_steps
    inst.get_node_by_content = fake_get_node_by_content

    # Prepare problems dict respecting ordering
    problems = {
        "prob1": {"problem": "p1_start", "label": "L1"},
        # For prob2, mark idea12 as used by adding to used_idea_id_set to force exclusion
        "prob2": {"problem": "p2_start", "label": "L2"},
    }
    # mark id 12 as used so idea12 will be skipped
    inst.used_idea_id_set.add(12)

    # Run sample_ideas
    out = idea_pool_mod.DSKnowledgeBase.sample_ideas(
        inst,
        problems,
        scenario_desc="s",
        exp_feedback_list_desc="f",
        sota_exp_desc="sota",
        competition_desc="none",
    )

    # Validate API was called
    assert fake_api.called is True
    # Validate problems were updated according to the fake response:
    # For prob1: picked 1 -> first accepted is idea10
    assert out["prob1"]["idea"] == "appendix10"
    assert out["prob1"]["idea_node_id"] == 10

    # For prob2: idea12 was excluded; only idea13 remains; picked 0 -> index -1 -> idea13
    assert out["prob2"]["idea"] == "appendix13"
    assert out["prob2"]["idea_node_id"] == 13


def test_sample_ideas_with_competition_and_edge_cases(monkeypatch):
    """
    Test competition exclusion and used_id exclusion together and ensure indexing behavior is correct.
    Also check that if picked_id is 0, negative index selection (picked_id - 1) selects last element.
    Adjusted to ensure deterministic accepted idea ordering.
    """
    # We'll craft a response that uses picked_id 0 for "probC" to exercise picked_id - 1 path
    response = json.dumps({"probA": 1, "probC": 0})
    fake_api = setup_common_monkeypatches(monkeypatch, response)

    inst = make_instance_without_init()
    # Ensure no used ids so the first candidate can be accepted deterministically
    inst.used_idea_id_set = set()

    # Create competition node
    competition_node = FakeNode(999, appendix="comp")

    # Create idea nodes:
    idea201 = FakeNode(201, appendix="appendix201", neighbors=[])
    # idea202 will be excluded because it neighbors the competition node
    idea202 = FakeNode(202, appendix="appendix202", neighbors=[competition_node])
    # idea203 will be accepted for probC
    idea203 = FakeNode(203, appendix="appendix203", neighbors=[])

    # Map start nodes to idea nodes
    start_to_idea = {
        "sa1": idea201,
        "sa2": idea202,
        "sa3": idea203,
        "sc1": idea203,  # for probC only one accepted idea
    }

    def fake_semantic_search(node, constraint_labels):
        # Return different start node lists based on the problem string given
        return {
            "probA_start": ["sa1", "sa2", "sa3"],  # sa1 accepted first
            "probC_start": ["sc1"],  # only one start, accepted
        }[node]

    def fake_get_nodes_within_steps(start_node, steps, constraint_labels):
        return [start_to_idea[start_node]]

    def fake_get_node_by_content(content):
        # return the competition node when asking for the competition description
        if content == "competition_here":
            return competition_node
        return None

    inst.semantic_search = fake_semantic_search
    inst.get_nodes_within_steps = fake_get_nodes_within_steps
    inst.get_node_by_content = fake_get_node_by_content

    problems = {
        "probA": {"problem": "probA_start", "label": "LA"},
        "probC": {"problem": "probC_start", "label": "LC"},
    }

    out = idea_pool_mod.DSKnowledgeBase.sample_ideas(
        inst,
        problems,
        scenario_desc="sc",
        exp_feedback_list_desc="ef",
        sota_exp_desc="sota",
        competition_desc="competition_here",
    )

    # API called
    assert fake_api.called is True

    # For probA: accepted first idea should be idea201 (id 201) because used set is empty and sa1 is first accepted
    assert out["probA"]["idea"] == "appendix201"
    assert out["probA"]["idea_node_id"] == 201

    # For probC: picked_id was 0 in response -> picked_id < len is True (0 < 1) and index is -1 -> last element (which is idea203)
    assert out["probC"]["idea"] == "appendix203"
    assert out["probC"]["idea_node_id"] == 203
