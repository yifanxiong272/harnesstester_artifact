# file: gpt_researcher/skills/deep_research.py:536-600
# asked: {"lines": [538, 539, 542, 544, 545, 547, 548, 549, 550, 552, 553, 554, 555, 556, 560, 563, 564, 565, 566, 570, 571, 572, 573, 574, 576, 579, 580, 583, 586, 587, 590, 591, 594, 595, 596, 597, 600], "branches": [[563, 564], [563, 570], [571, 572], [571, 579], [573, 574], [573, 576], [579, 580], [579, 583], [590, 591], [590, 594]]}
# gained: {"lines": [538, 539, 542, 544, 545, 547, 548, 549, 550, 552, 553, 554, 555, 556, 560, 563, 564, 565, 566, 570, 571, 572, 573, 574, 576, 579, 580, 583, 586, 587, 590, 591, 594, 595, 596, 597, 600], "branches": [[563, 564], [563, 570], [571, 572], [571, 579], [573, 574], [573, 576], [579, 580], [579, 583], [590, 591], [590, 594]]}

import asyncio
import pytest

import types

import gpt_researcher.skills.deep_research as dr_mod
from gpt_researcher.skills.deep_research import DeepResearchSkill


class DummyCfg:
    def __init__(self, breadth=2, depth=1, concurrency=1, config_path=None):
        self.deep_research_breadth = breadth
        self.deep_research_depth = depth
        self.deep_research_concurrency = concurrency
        self.config_path = config_path


class DummyResearcher:
    def __init__(self, query="What is X?", costs_start=0, headers=None, visited_urls=None, log_handler=False):
        self.cfg = DummyCfg()
        self.websocket = None
        self.tone = None
        self.config_path = None
        self.headers = headers or {}
        self.visited_urls = visited_urls or []
        self.query = query
        self._costs = costs_start
        self.log_handler = log_handler
        self.context = ""
        self.research_sources = []
        self.visited_urls = []
        # record for _log_event calls
        self._logged_events = []

    def get_costs(self):
        return self._costs

    async def _log_event(self, *args, **kwargs):
        # store call for assertions
        self._logged_events.append((args, kwargs))


@pytest.mark.asyncio
async def test_run_with_citations_and_sources_and_loghandler(monkeypatch):
    # Prepare researcher with initial costs
    researcher = DummyResearcher(query="Initial Q?", costs_start=10, log_handler=True)

    # Create DeepResearchSkill instance
    skill = DeepResearchSkill(researcher)

    # Monkeypatch trim_context_to_word_limit to be identity (returns same list)
    monkeypatch.setattr(dr_mod, "trim_context_to_word_limit", lambda ctx: ctx)

    # Prepare generate_research_plan to return 2 follow-up questions
    async def fake_generate_research_plan(query):
        return ["Q1", "Q2"]
    skill.generate_research_plan = types.MethodType(lambda self, q: fake_generate_research_plan(q), skill)

    # Prepare deep_research to update researcher costs and return structured results
    async def fake_deep_research(self, query, breadth, depth, learnings=None, citations=None, visited_urls=None, on_progress=None):
        # Simulate spending some cost
        researcher._costs = 15.0
        # Provide two learnings, one has a citation, one doesn't
        results = {
            "learnings": ["Finding A", "Finding B"],
            "citations": {"Finding A": "http://example.com/a"},  # only for Finding A
            "context": ["Extra context item"],
            "visited_urls": ["http://example.com/a", "http://example.com/b"],
            "sources": ["http://example.com/a"]
        }
        return results

    # Bind fake deep_research to the instance
    skill.deep_research = types.MethodType(fake_deep_research, skill)

    # Run and capture result
    result_context = await skill.run(on_progress=None)

    # Expected context: learning with citation, learning without, then the extra context item, joined by newline
    expected_list = [
        "Finding A [Source: http://example.com/a]",
        "Finding B",
        "Extra context item"
    ]
    expected_context = "\n".join(expected_list)

    assert result_context == expected_context
    # Ensure researcher attributes updated
    assert researcher.context == expected_context
    assert researcher.visited_urls == ["http://example.com/a", "http://example.com/b"]
    assert researcher.research_sources == ["http://example.com/a"]
    # Ensure _log_event was called once and has step deep_research_costs in kwargs
    assert len(researcher._logged_events) == 1
    args, kwargs = researcher._logged_events[0]
    # kwargs should include step and details with research_costs and total_costs
    assert kwargs.get("step") == "deep_research_costs"
    details = kwargs.get("details", {})
    assert "research_costs" in details and details["research_costs"] == pytest.approx(5.0)
    assert "total_costs" in details and details["total_costs"] == pytest.approx(15.0)


@pytest.mark.asyncio
async def test_run_without_citations_no_sources_no_context_no_loghandler(monkeypatch):
    # Researcher without log handler and zero cost change
    researcher = DummyResearcher(query="Another Q?", costs_start=0, log_handler=False)

    skill = DeepResearchSkill(researcher)

    # Monkeypatch trim_context_to_word_limit to truncate to at most 1 word per element (simulate trimming)
    # For clarity, just return the input list unchanged (identity)
    monkeypatch.setattr(dr_mod, "trim_context_to_word_limit", lambda ctx: ctx)

    # generate_research_plan returns a single follow-up question
    async def fake_generate_research_plan(query):
        return ["OnlyQ"]
    skill.generate_research_plan = types.MethodType(lambda self, q: fake_generate_research_plan(q), skill)

    # deep_research returns learnings but no citations, no context, no sources
    async def fake_deep_research(self, query, breadth, depth, learnings=None, citations=None, visited_urls=None, on_progress=None):
        # costs unchanged
        researcher._costs = 0.0
        return {
            "learnings": ["Solo Finding"],
            "citations": {},  # no citations
            "context": [],  # no extra context
            "visited_urls": [],
            # no 'sources' key
        }

    skill.deep_research = types.MethodType(fake_deep_research, skill)

    result_context = await skill.run(on_progress=None)

    # Since no citations and no extra context, the context should be just the learning joined (single item)
    expected_context = "Solo Finding"
    assert result_context == expected_context
    assert researcher.context == expected_context
    assert researcher.visited_urls == []
    # research_sources should remain default empty list (no 'sources' in results)
    assert researcher.research_sources == []
    # No log events should have been recorded
    assert researcher._logged_events == []
