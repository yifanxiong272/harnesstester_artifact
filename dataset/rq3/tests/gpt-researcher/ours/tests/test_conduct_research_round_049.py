import asyncio
import types
import pytest

import gpt_researcher.agent as agent_module
from gpt_researcher.agent import GPTResearcher
from gpt_researcher.utils.enum import ReportType


class SimpleAsyncTracker:
    """Helper to provide async callables and record calls for assertions."""
    def __init__(self):
        self.calls = []

    async def noop_log(self, event_type, **kwargs):
        # Record a shallow copy of kwargs for determinism
        self.calls.append((event_type, dict(kwargs)))


@pytest.mark.asyncio
async def test_conduct_research_deep_research_round_049():
    # Arrange: create GPTResearcher instance without running __init__
    researcher = object.__new__(GPTResearcher)

    # Minimal attributes used by conduct_research
    researcher.query = "q"
    researcher.report_type = ReportType.DeepResearch.value
    researcher.agent = None
    researcher.role = None
    researcher.role = None
    researcher.parent_query = None
    researcher.cfg = None
    researcher.headers = None
    researcher.prompt_family = None
    researcher.kwargs = {}

    tracker = SimpleAsyncTracker()
    # Patch _log_event to record calls
    researcher._log_event = tracker.noop_log

    # Provide a deep_researcher flag and an async _handle_deep_research
    async def fake_handle_deep_research(on_progress):
        # simulate doing some deep research and return a special sentinel
        return {"deep": True, "query": researcher.query}

    researcher.deep_researcher = True
    # bind the handler method name used in conduct_research
    researcher._handle_deep_research = fake_handle_deep_research

    # Act
    result = await GPTResearcher.conduct_research(researcher, on_progress=None)

    # Assert: branch taken returning deep_research result and current step set
    assert result == {"deep": True, "query": "q"}
    # _current_step should be set to deep_research as per the branch
    assert getattr(researcher, "_current_step") == "deep_research"
    # _log_event should have been called at least once for start
    assert any(ev[0] == "research" for ev in tracker.calls), "expected a research start log"


@pytest.mark.asyncio
async def test_conduct_research_agent_selection_and_image_generation_round_049(monkeypatch):
    # Arrange: create instance bypassing __init__ and set attributes referenced
    researcher = object.__new__(GPTResearcher)
    researcher.query = "my query"
    researcher.report_type = "not_deep"
    researcher.agent = None
    researcher.role = None
    researcher.parent_query = "parent"
    researcher.cfg = {"some": "cfg"}
    researcher.headers = {"h": "v"}
    researcher.prompt_family = "pf"
    researcher.kwargs = {"extra": 1}
    researcher._current_step = None

    # Track logs
    logs = []

    async def fake_log(event_type, **kwargs):
        logs.append((event_type, dict(kwargs)))

    researcher._log_event = fake_log

    # Patch choose_agent at module level to avoid external behavior
    async def fake_choose_agent(**kwargs):
        # Ensure expected keys are being forwarded
        assert "query" in kwargs and kwargs["query"] == "my query"
        # return pair as the real function would
        return ("agentX", "roleY")

    monkeypatch.setattr(agent_module, "choose_agent", fake_choose_agent)

    # Provide add_costs callable referenced as cost_callback
    def add_costs(cost):
        # simple side effect, attach to researcher for observation
        researcher._last_cost = cost

    researcher.add_costs = add_costs

    # Provide a research_conductor with an async conduct_research returning a list
    class FakeResearchConductor:
        async def conduct_research(self_inner):
            return ["ctx1", "ctx2"]

    researcher.research_conductor = FakeResearchConductor()

    # Provide image_generator that is enabled and returns images
    class FakeImageGenerator:
        def __init__(self):
            self.enabled = True

        def is_enabled(self):
            return self.enabled

        async def plan_and_generate_images(self, context, query, research_id):
            # Assert that context is stringified form of context list
            assert isinstance(context, str)
            assert query == researcher.query
            assert research_id == researcher._generate_research_id()
            return ["img1.png", "img2.png"]

    researcher.image_generator = FakeImageGenerator()

    # Provide a deterministic _generate_research_id
    researcher._generate_research_id = lambda: "research-123"

    # Ensure context attribute will be filled by research_conductor
    researcher.context = None

    # Act
    result_context = await GPTResearcher.conduct_research(researcher, on_progress=None)

    # Assert: agent and role were selected
    assert researcher.agent == "agentX"
    assert researcher.role == "roleY"

    # research step should be set and returned context matches fake conductor output
    assert researcher._current_step == "research"
    assert result_context == ["ctx1", "ctx2"]

    # available_images should be set from the fake image generator
    assert researcher.available_images == ["img1.png", "img2.png"]

    # verify that logs include certain expected actions in order
    # first call should be research start
    assert any(call[0] == "research" and call[1].get("step") == "start" for call in logs)
    # logs should include action choose_agent and action agent_selected
    assert any(call[0] == "action" and call[1].get("action") == "choose_agent" for call in logs)
    assert any(call[0] == "action" and call[1].get("action") == "agent_selected" for call in logs)
    # logs should include planning_images and images_pre_generated
    assert any(call[0] == "research" and call[1].get("step") == "planning_images" for call in logs)
    assert any(call[0] == "research" and call[1].get("step") == "images_pre_generated" for call in logs)
