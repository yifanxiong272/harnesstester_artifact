# file: gpt_researcher/skills/deep_research.py:372-534
# asked: {"lines": [383, 384, 385, 386, 387, 388, 389, 391, 393, 394, 397, 398, 399, 400, 402, 403, 404, 405, 406, 409, 411, 412, 413, 414, 415, 416, 418, 419, 420, 423, 424, 425, 426, 427, 429, 430, 434, 437, 438, 441, 442, 443, 447, 448, 449, 450, 452, 453, 454, 455, 456, 457, 458, 459, 462, 463, 464, 465, 466, 467, 470, 471, 472, 475, 476, 477, 480, 481, 482, 483, 484, 485, 486, 487, 490, 491, 492, 493, 496, 497, 498, 502, 503, 504, 505, 506, 507, 508, 509, 512, 513, 514, 515, 516, 517, 518, 521, 522, 525, 526, 528, 529, 530, 531, 532, 533], "branches": [[384, 385], [384, 386], [386, 387], [386, 388], [388, 389], [388, 391], [393, 394], [393, 397], [415, 416], [415, 418], [449, 450], [449, 452], [476, 477], [476, 480], [480, 481], [480, 521], [484, 485], [484, 486], [486, 487], [486, 490], [490, 480], [490, 491], [515, 516], [515, 517], [517, 480], [517, 518]]}
# gained: {"lines": [383, 384, 385, 386, 387, 388, 389, 391, 393, 394, 397, 398, 399, 400, 402, 403, 404, 405, 406, 409, 411, 412, 413, 414, 415, 416, 418, 419, 420, 423, 424, 425, 426, 427, 429, 430, 434, 437, 438, 441, 442, 443, 447, 448, 449, 450, 452, 453, 454, 455, 456, 457, 458, 459, 462, 463, 464, 465, 466, 467, 470, 471, 472, 475, 476, 477, 480, 481, 482, 483, 484, 485, 486, 487, 490, 491, 492, 493, 496, 497, 498, 502, 503, 504, 505, 506, 507, 508, 509, 512, 513, 514, 515, 516, 517, 518, 521, 522, 525, 526, 528, 529, 530, 531, 532, 533], "branches": [[384, 385], [384, 386], [386, 387], [386, 388], [388, 389], [388, 391], [393, 394], [415, 416], [449, 450], [476, 477], [480, 481], [480, 521], [484, 485], [486, 487], [490, 480], [490, 491], [515, 516], [517, 518]]}

import asyncio
from types import SimpleNamespace
import pytest

from gpt_researcher.skills import deep_research as dr_module


@pytest.mark.asyncio
async def test_deep_research_single_level_success(monkeypatch):
    # Prepare a fake researcher object to initialize DeepResearchSkill
    fake_researcher = SimpleNamespace(
        cfg=SimpleNamespace(deep_research_breadth=4, deep_research_depth=2, deep_research_concurrency=2, config_path="/tmp"),
        websocket=None,
        tone="neutral",
        headers={"User-Agent": "test"},
        visited_urls=set(),
        mcp_configs={},
        mcp_strategy=None
    )

    skill = dr_module.DeepResearchSkill(fake_researcher)

    # Monkeypatch generate_search_queries to return a single query
    async def fake_generate_search_queries(self, query, num_queries=3):
        return [{'query': 'test query', 'researchGoal': 'test goal'}]

    monkeypatch.setattr(dr_module.DeepResearchSkill, "generate_search_queries", fake_generate_search_queries)

    # Monkeypatch GPTResearcher used inside deep_research by placing it on the package
    class FakeGPTResearcher:
        def __init__(self, *args, **kwargs):
            self._query = kwargs.get('query', args[0] if args else None)
            self.visited_urls = {"http://example.com"}
            self.research_sources = ["source1"]

        async def conduct_research(self):
            # return a list of context strings
            return [f"context for {self._query}"]

    monkeypatch.setattr("gpt_researcher.GPTResearcher", FakeGPTResearcher, raising=False)

    # Monkeypatch process_research_results to return learnings, followUpQuestions, citations
    async def fake_process_research_results(self, query, context, num_learnings=3):
        return {
            'learnings': [f"learning from {query}"],
            'followUpQuestions': ["What is X?", "How does Y work?"],
            'citations': {"http://example.com": "Example"}
        }

    monkeypatch.setattr(dr_module.DeepResearchSkill, "process_research_results", fake_process_research_results)

    # Monkeypatch trim_context_to_word_limit to simply return the context unchanged (and to ensure it's called)
    monkeypatch.setattr(dr_module, "trim_context_to_word_limit", lambda all_context: all_context)

    # Capture progress updates
    progresses = []

    def on_progress(p):
        # store shallow copy of attributes we expect
        progresses.append((p.current_depth, p.current_breadth, p.completed_queries, getattr(p, "current_query", None)))

    # Run deep_research with depth=1 to avoid recursion
    result = await skill.deep_research(query="root query", breadth=1, depth=1, on_progress=on_progress)

    # Assertions about return structure
    assert isinstance(result, dict)
    assert 'learnings' in result and isinstance(result['learnings'], list)
    assert any("learning from" in l for l in result['learnings'])
    assert set(result['visited_urls']) == {"http://example.com"}
    assert result['citations'] == {"http://example.com": "Example"}
    assert result['context'] == ["context for test query"]
    assert result['sources'] == ["source1"]

    # Ensure progress was reported at least once and shows completed queries increment
    assert len(progresses) >= 1
    # completed queries should be 1 at the end (since one query processed successfully)
    assert progresses[-1][2] == 1


@pytest.mark.asyncio
async def test_deep_research_recursive_and_merge(monkeypatch):
    fake_researcher = SimpleNamespace(
        cfg=SimpleNamespace(deep_research_breadth=4, deep_research_depth=3, deep_research_concurrency=2, config_path="/tmp"),
        websocket=None,
        tone="neutral",
        headers={},
        visited_urls=set(),
        mcp_configs={"some": "config"},
        mcp_strategy="strategy"
    )
    skill = dr_module.DeepResearchSkill(fake_researcher)

    # Keep counters to assert recursion happened
    call_counts = {"generate": 0, "process": 0}

    async def fake_generate_search_queries(self, query, num_queries=3):
        call_counts["generate"] += 1
        # For top-level (not containing "Previous research goal") return one query
        if "Previous research goal" in query:
            return [{'query': 'deep sub query', 'researchGoal': 'subgoal'}]
        return [{'query': 'root q', 'researchGoal': 'root goal'}]

    monkeypatch.setattr(dr_module.DeepResearchSkill, "generate_search_queries", fake_generate_search_queries)

    class FakeGPTResearcher:
        def __init__(self, *args, **kwargs):
            self._query = kwargs.get('query', args[0] if args else None)
            self.visited_urls = {f"http://{self._query}.example.com"}
            self.research_sources = [f"src-{self._query}"]

        async def conduct_research(self):
            await asyncio.sleep(0)  # ensure it's truly async
            return [f"context for {self._query}"]

    monkeypatch.setattr("gpt_researcher.GPTResearcher", FakeGPTResearcher, raising=False)

    async def fake_process_research_results(self, query, context, num_learnings=3):
        call_counts["process"] += 1
        if "root q" in query:
            return {
                'learnings': ["root learning"],
                'followUpQuestions': ["follow1", "follow2"],
                'citations': {"http://root.example.com": "Root"}
            }
        else:
            return {
                'learnings': ["sub learning"],
                'followUpQuestions': [],
                'citations': {"http://sub.example.com": "Sub"}
            }

    monkeypatch.setattr(dr_module.DeepResearchSkill, "process_research_results", fake_process_research_results)

    # Keep trim as identity but ensure it's monkeypatched
    monkeypatch.setattr(dr_module, "trim_context_to_word_limit", lambda all_context: all_context)

    progresses = []

    def on_progress(p):
        progresses.append((p.current_depth, p.current_breadth, p.completed_queries))

    # Run with depth=2 so recursion happens once
    result = await skill.deep_research(query="initial query", breadth=1, depth=2, on_progress=on_progress)

    # Validate that generate_search_queries and process_research_results were called more than once (recursion)
    assert call_counts["generate"] >= 2
    assert call_counts["process"] >= 2

    # Validate merged learnings include both root and sub learnings
    assert set(result['learnings']) >= {"root learning", "sub learning"}

    # Validate citations merged
    assert "http://root.example.com" in result['citations']
    assert "http://sub.example.com" in result['citations']

    # Validate context contains both contexts
    assert any("context for root q" in c for c in result['context'])
    assert any("context for deep sub query" in c for c in result['context'])

    # Validate sources aggregated
    assert any("src-root q" in s for s in result['sources'])
    assert any("src-deep sub query" in s for s in result['sources'])

    # Progress should show deeper depth increment at some point
    assert any(p[0] >= 1 for p in progresses)


@pytest.mark.asyncio
async def test_deep_research_handles_query_processing_exception(monkeypatch):
    fake_researcher = SimpleNamespace(
        cfg=SimpleNamespace(deep_research_breadth=2, deep_research_depth=1, deep_research_concurrency=1, config_path="/tmp"),
        websocket=None,
        tone="neutral",
        headers={},
        visited_urls=set(),
        mcp_configs={},
        mcp_strategy=None
    )
    skill = dr_module.DeepResearchSkill(fake_researcher)

    # generate one query
    async def fake_generate_search_queries(self, query, num_queries=3):
        return [{'query': 'will fail', 'researchGoal': 'failgoal'}]

    monkeypatch.setattr(dr_module.DeepResearchSkill, "generate_search_queries", fake_generate_search_queries)

    # Fake GPTResearcher that raises during conduct_research to trigger exception handling
    class RaisingGPTResearcher:
        def __init__(self, *args, **kwargs):
            pass

        async def conduct_research(self):
            raise RuntimeError("simulated failure during conduct_research")

    monkeypatch.setattr("gpt_researcher.GPTResearcher", RaisingGPTResearcher, raising=False)

    # Make process_research_results present but it should not be called (since conduct_research fails)
    async def fake_process_research_results(self, query, context, num_learnings=3):
        return {'learnings': [], 'followUpQuestions': [], 'citations': {}}

    monkeypatch.setattr(dr_module.DeepResearchSkill, "process_research_results", fake_process_research_results)

    # Ensure trim_context_to_word_limit exists
    monkeypatch.setattr(dr_module, "trim_context_to_word_limit", lambda all_context: all_context)

    # Capture prints/errors by providing an on_progress
    progresses = []

    def on_progress(p):
        progresses.append((p.current_depth, p.current_breadth, p.completed_queries))

    result = await skill.deep_research(query="root", breadth=1, depth=1, on_progress=on_progress)

    # Since the only query processing failed, results should be largely empty but still well-formed
    assert result['learnings'] == []
    assert result['visited_urls'] == []
    assert result['citations'] == {}
    assert result['context'] == []
    assert result['sources'] == []
    # Progress should reflect attempted processing (completed_queries should be 0)
    assert any(isinstance(p[2], int) for p in progresses)
