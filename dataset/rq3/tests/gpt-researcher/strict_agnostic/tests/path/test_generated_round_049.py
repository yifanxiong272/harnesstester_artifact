import types
import pytest

from gpt_researcher.agent import GPTResearcher, ReportType

# The tests below call the unbound method GPTResearcher.conduct_research
# with a lightweight fake 'self' object whose attributes are controlled
# to exercise branches in the implementation deterministically.

@pytest.mark.asyncio
async def test_deep_research_branch_round_049():
    # Prepare a minimal fake instance with attributes used by the method
    calls = []

    async def fake_log_event(event_type, **kwargs):
        # record events for assertions
        calls.append((event_type, kwargs))

    async def fake_handle_deep_research(on_progress=None):
        # emulate deep research result
        calls.append(("_handle_deep_research_called", {}))
        return "deep_result"

    self_obj = types.SimpleNamespace()
    self_obj.query = "q"
    # Use the DeepResearch enum value to trigger the deep-research branch
    self_obj.report_type = ReportType.DeepResearch.value
    # Ensure deep_researcher exists and handler present
    self_obj.deep_researcher = True
    self_obj._handle_deep_research = fake_handle_deep_research
    self_obj._log_event = fake_log_event
    # The implementation logs self.agent and self.role at the start of the method,
    # so ensure these attributes exist (they can be None)
    self_obj.agent = None
    self_obj.role = None

    # Call the unbound async function with our fake self
    result = await GPTResearcher.conduct_research(self_obj, on_progress=None)

    # Assertions: deep branch should return the deep research result and set expected calls
    assert result == "deep_result"
    # verify that start event was logged and that _handle_deep_research was invoked
    assert any(evt == "research" and kwargs.get("step") == "start" for evt, kwargs in calls), (
        "expected a research start log event"
    )
    assert any(tag == "_handle_deep_research_called" for tag, _ in calls), (
        "expected _handle_deep_research to be called"
    )


@pytest.mark.asyncio
async def test_agent_selection_and_image_generation_round_049(monkeypatch):
    # This test exercises the non-deep path where agent selection occurs,
    # research is conducted, and image generation is enabled.

    # Capture events
    events = []

    async def fake_log_event(event_type, **kwargs):
        events.append((event_type, kwargs))

    # Stub choose_agent to avoid external dependencies
    async def fake_choose_agent(**kwargs):
        # return a tuple (agent, role)
        return ("chosen_agent", "chosen_role")

    monkeypatch.setattr("gpt_researcher.agent.choose_agent", fake_choose_agent)

    # Research conductor that returns a list context
    async def fake_conduct_research():
        return ["ctx1", "ctx2"]

    research_conductor = types.SimpleNamespace(conduct_research=fake_conduct_research)

    # Image generator stub that is enabled and returns generated images
    async def fake_plan_and_generate_images(context, query, research_id):
        # verify that context is the joined string of ctx list (deterministic)
        assert isinstance(context, str)
        assert "ctx1" in context and "ctx2" in context
        return ["img_a", "img_b"]

    image_generator = types.SimpleNamespace(
        is_enabled=lambda: True,
        plan_and_generate_images=fake_plan_and_generate_images,
    )

    # Fake self object
    self_obj = types.SimpleNamespace()
    self_obj.query = "search-query"
    # Use some non-deep value to avoid deep-research branch
    self_obj.report_type = "quick"
    # Force agent/role to be missing to trigger agent selection
    self_obj.agent = None
    self_obj.role = None
    self_obj.cfg = None
    self_obj.parent_query = None
    self_obj.add_costs = lambda *a, **k: None
    self_obj.headers = {}
    self_obj.prompt_family = None
    self_obj.kwargs = {}
    self_obj._log_event = fake_log_event
    self_obj.research_conductor = research_conductor
    self_obj.image_generator = image_generator
    self_obj._generate_research_id = lambda: "research-id-123"

    # Call the method under test
    result = await GPTResearcher.conduct_research(self_obj, on_progress=None)

    # Post-conditions: context returned should be the list from fake_conduct_research
    assert result == ["ctx1", "ctx2"]

    # Agent selection should have populated agent and role
    assert self_obj.agent == "chosen_agent"
    assert self_obj.role == "chosen_role"

    # _current_step should be set to research after research conductor runs
    assert getattr(self_obj, "_current_step", None) == "research"

    # Image generation should have been invoked and available_images set
    assert hasattr(self_obj, "available_images")
    assert self_obj.available_images == ["img_a", "img_b"]

    # Verify logged events include planning_images and images_pre_generated with correct count
    assert any(evt == "research" and kwargs.get("step") == "planning_images" for evt, kwargs in events), (
        "expected planning_images log"
    )
    assert any(evt == "research" and kwargs.get("step") == "images_pre_generated" and kwargs.get("details", {}).get("images_count") == 2 for evt, kwargs in events), (
        "expected images_pre_generated log with images_count == 2"
    )
