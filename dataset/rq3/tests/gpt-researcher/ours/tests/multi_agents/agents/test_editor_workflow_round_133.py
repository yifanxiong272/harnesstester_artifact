import types
import pytest

from multi_agents.agents import editor


def test_editor_create_workflow_round_133(monkeypatch):
    """Validate that EditorAgent._create_workflow constructs the StateGraph with
    the expected nodes, edges, entry point, and conditional mapping.

    This test patches the symbols the implementation resolves (StateGraph, END,
    DraftState) with deterministic fakes and stubs EditorAgent._initialize_agents
    to return controlled agent callables. It then exercises _create_workflow and
    asserts observable behavior.
    """

    # Create sentinels for DraftState and END so we can assert they are propagated
    DRAFT_SENTINEL = object()
    END_SENTINEL = object()

    # Fake StateGraph that records calls made by _create_workflow
    class FakeStateGraph:
        def __init__(self, initial_state):
            # capture the initial state provided
            self.initial_state = initial_state
            self.nodes = {}
            self.entry_point = None
            self.edges = []
            self.conditional = None

        def add_node(self, name, handler):
            self.nodes[name] = handler

        def set_entry_point(self, name):
            self.entry_point = name

        def add_edge(self, src, dst):
            self.edges.append((src, dst))

        def add_conditional_edges(self, node, func, mapping):
            # store the conditional tuple for later inspection
            self.conditional = (node, func, mapping)

    # Patch the module-level symbols where EditorAgent resolves them
    monkeypatch.setattr(editor, "StateGraph", FakeStateGraph)
    monkeypatch.setattr(editor, "END", END_SENTINEL)
    monkeypatch.setattr(editor, "DraftState", DRAFT_SENTINEL)

    # Create simple agent stubs with the exact attributes the editor expects
    class ResearchAgentStub:
        def __init__(self):
            # this callable should be placed into the "researcher" node
            self.run_depth_research = lambda state: "researcher_called"

    class ReviewerAgentStub:
        def __init__(self):
            self.run = lambda state: "reviewer_called"

    class ReviserAgentStub:
        def __init__(self):
            self.run = lambda state: "reviser_called"

    research_stub = ResearchAgentStub()
    reviewer_stub = ReviewerAgentStub()
    reviser_stub = ReviserAgentStub()

    # Stub _initialize_agents to return the controlled mapping
    def fake_initialize_agents(self):
        return {
            "research": research_stub,
            "reviewer": reviewer_stub,
            "reviser": reviser_stub,
        }

    monkeypatch.setattr(editor.EditorAgent, "_initialize_agents", fake_initialize_agents)

    # Instantiate EditorAgent with dummy constructor args (matches signature)
    agent = editor.EditorAgent(None, False, "tone", {})

    # Call the method under test
    workflow = agent._create_workflow()

    # Assertions: the returned object should be our FakeStateGraph and configured
    assert isinstance(workflow, FakeStateGraph)

    # The initial state passed into StateGraph should be the DraftState sentinel
    assert workflow.initial_state is DRAFT_SENTINEL

    # Nodes: researcher should be wired to research_stub.run_depth_research
    assert "researcher" in workflow.nodes
    assert workflow.nodes["researcher"] is research_stub.run_depth_research

    # reviewer and reviser nodes should be present and point to correct callables
    assert workflow.nodes["reviewer"] is reviewer_stub.run
    assert workflow.nodes["reviser"] is reviser_stub.run

    # Entry point must be researcher
    assert workflow.entry_point == "researcher"

    # Edges must include researcher->reviewer and reviser->reviewer (order not required)
    assert ("researcher", "reviewer") in workflow.edges
    assert ("reviser", "reviewer") in workflow.edges

    # Conditional edges recorded: ensure node is reviewer and mapping uses our END sentinel
    assert workflow.conditional is not None
    cond_node, cond_func, cond_map = workflow.conditional
    assert cond_node == "reviewer"

    # The lambda in the code should return "accept" when draft["review"] is None
    result_accept = cond_func({"review": None})
    assert result_accept == "accept"
    # And "revise" when draft["review"] is not None
    result_revise = cond_func({"review": "not-none"})
    assert result_revise == "revise"

    # Mapping should point "accept" to END_SENTINEL and "revise" to the "reviser" target
    assert cond_map["accept"] is END_SENTINEL
    assert cond_map["revise"] == "reviser"
