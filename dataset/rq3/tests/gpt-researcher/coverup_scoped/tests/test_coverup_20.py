# file: gpt_researcher/skills/deep_research.py:536-600
# asked: {"lines": [538, 539, 542, 544, 545, 547, 548, 549, 550, 552, 553, 554, 555, 556, 560, 563, 564, 565, 566, 570, 571, 572, 573, 574, 576, 579, 580, 583, 586, 587, 590, 591, 594, 595, 596, 597, 600], "branches": [[563, 564], [563, 570], [571, 572], [571, 579], [573, 574], [573, 576], [579, 580], [579, 583], [590, 591], [590, 594]]}
# gained: {"lines": [538, 539, 542, 544, 545, 547, 548, 549, 550, 552, 553, 554, 555, 556, 560, 563, 564, 565, 566, 570, 571, 572, 573, 574, 576, 579, 580, 583, 586, 587, 590, 591, 594, 595, 596, 597, 600], "branches": [[563, 564], [563, 570], [571, 572], [571, 579], [573, 574], [573, 576], [579, 580], [579, 583], [590, 591], [590, 594]]}

import asyncio
import types
import pytest

import gpt_researcher.skills.deep_research as dr_mod
from gpt_researcher.skills.deep_research import DeepResearchSkill


class DummyCfg:
    def __init__(self, breadth=3, depth=2, concurrency=2, config_path=None):
        self.deep_research_breadth = breadth
        self.deep_research_depth = depth
        self.deep_research_concurrency = concurrency
        self.config_path = config_path


class DummyResearcher:
    def __init__(self):
        self.cfg = DummyCfg(breadth=5, depth=3, concurrency=4, config_path="/tmp/cfg")
        self.websocket = None
        self.tone = "neutral"
        self.headers = {"h": "v"}
        self.visited_urls = []
        self.query = "What is testing?"
        self.context = ""
        self.learnings = []
        self.research_sources = []
        self._cost = 10.0
        self.log_handler = True
        self._logged_events = []

    def get_costs(self):
        return self._cost

    async def _log_event(self, *args, **kwargs):
        # record calls for assertions
        self._logged_events.append((args, kwargs))


@pytest.mark.asyncio
async def test_run_with_log_handler_and_citations(monkeypatch):
    researcher = DummyResearcher()

    # Prepare module-level replacements
    # Capture logger.info calls
    logged_infos = []

    class DummyLogger:
        def info(self, msg):
            logged_infos.append(msg)

    monkeypatch.setattr(dr_mod, "logger", DummyLogger())

    # Replace trim_context_to_word_limit to return the list unchanged
    monkeypatch.setattr(dr_mod, "trim_context_to_word_limit", lambda ctx: ctx)

    # Create follow-up questions for generate_research_plan
    async def fake_generate_research_plan(self, query, num_questions=3):
        assert query == researcher.query
        # Return 2 follow-up questions to exercise answers list creation
        return ["Q1", "Q2"]

    monkeypatch.setattr(DeepResearchSkill, "generate_research_plan", fake_generate_research_plan)

    # Replace deep_research to produce results and increment researcher's costs
    async def fake_deep_research(self, query, breadth, depth, learnings=None, citations=None, visited_urls=None, on_progress=None):
        # ensure the combined_query contains the initial query
        assert "Initial Query: " in query
        # simulate some work and increase costs
        researcher._cost += 5.0
        return {
            "learnings": ["L1", "L2"],
            "citations": {"L1": "http://a", "L2": ""},
            "context": ["ctx1", "ctx2"],
            "visited_urls": ["u1", "u2"],
            "sources": ["s1"]
        }

    monkeypatch.setattr(DeepResearchSkill, "deep_research", fake_deep_research)

    skill = DeepResearchSkill(researcher)

    # Run
    result_context = await skill.run(on_progress=None)

    # Assertions:
    # researcher.context should be newline-joined items from learnings(with citation) + other context
    expected_context_list = [
        "L1 [Source: http://a]",
        "L2",
        "ctx1",
        "ctx2"
    ]
    expected_context = "\n".join(expected_context_list)
    assert result_context == expected_context
    assert researcher.context == expected_context

    # visited_urls and research_sources set
    assert researcher.visited_urls == ["u1", "u2"]
    assert researcher.research_sources == ["s1"]

    # costs: initial 10 -> after deep_research 15 -> research_costs should be 5
    # _log_event should have been called once with research cost details
    assert len(researcher._logged_events) == 1
    args, kwargs = researcher._logged_events[0]
    # first arg is "research"
    assert args[0] == "research"
    # step kwarg
    assert kwargs.get("step") == "deep_research_costs"
    details = kwargs.get("details", {})
    assert details["research_costs"] == pytest.approx(5.0)
    assert details["total_costs"] == pytest.approx(15.0)

    # logger.info must have been called at least twice (execution time and costs)
    assert any("Total research execution time" in m for m in logged_infos)
    assert any("Total research costs" in m for m in logged_infos)


@pytest.mark.asyncio
async def test_run_without_log_handler_skips_logging(monkeypatch):
    researcher = DummyResearcher()
    researcher.log_handler = False  # ensure logging branch is skipped

    # Minimal replacements
    monkeypatch.setattr(dr_mod, "trim_context_to_word_limit", lambda ctx: ctx)
    monkeypatch.setattr(dr_mod, "logger", types.SimpleNamespace(info=lambda *a, **k: None))

    async def fake_generate_research_plan(self, query, num_questions=3):
        return []  # no follow-up questions

    monkeypatch.setattr(DeepResearchSkill, "generate_research_plan", fake_generate_research_plan)

    async def fake_deep_research(self, query, breadth, depth, learnings=None, citations=None, visited_urls=None, on_progress=None):
        # do not change costs here
        return {
            "learnings": [],
            "citations": {},
            # no 'context' key to exercise that branch (results.get('context') falsy)
            "visited_urls": [],
        }

    monkeypatch.setattr(DeepResearchSkill, "deep_research", fake_deep_research)

    skill = DeepResearchSkill(researcher)

    result = await skill.run(on_progress=None)

    # When there are no context entries, researcher.context becomes empty string
    assert result == ""
    assert researcher.context == ""
    # Ensure _log_event was not called
    assert researcher._logged_events == []
