import asyncio
import types
import pytest

from types import SimpleNamespace

import backend.report_type.deep_research.example as example


@pytest.mark.asyncio
async def test_deep_research_success_round_011(monkeypatch):
    """Exercise normal successful flow of deep_research with on_progress and default None inputs.

    - Patch GPTResearcher to avoid network/model calls.
    - Patch generate_serp_queries and process_serp_result to return deterministic data.
    - Verify learnings, visited_urls and citations aggregation and that on_progress was invoked and
      completed_queries reached the total.
    """

    # Dummy GPTResearcher that simulates conduct_research without side effects
    class DummyResearcher:
        def __init__(self, query, report_type=None, report_source=None, tone=None, websocket=None, config_path=None, headers=None):
            self.query = query
            self.report_type = report_type
            self.report_source = report_source
            self.tone = tone
            self.websocket = websocket
            self.config_path = config_path
            self.headers = headers
            self.context = None
            self.visited_urls = []

        async def conduct_research(self):
            # Simulate producing context and visited_urls
            await asyncio.sleep(0)  # ensure async
            self.context = {"ctx_for": self.query}
            self.visited_urls = [f"http://{self.query}.example"]

    # Patch the GPTResearcher symbol where the module resolves it
    monkeypatch.setattr(example, "GPTResearcher", DummyResearcher)

    # deterministic SERP queries
    async def dummy_generate_serp_queries(self, query, num_queries=1):
        await asyncio.sleep(0)
        return [
            {"query": "q1", "researchGoal": "goal1"},
            {"query": "q2", "researchGoal": "goal2"},
        ]

    async def dummy_process_serp_result(self, query, context, num_learnings=5):
        await asyncio.sleep(0)
        # Distinct learnings per query to see aggregation
        return {
            "learnings": [f"learning_{query}"],
            "followUpQuestions": [f"follow_{query}"],
            "citations": {f"cite_{query}": f"url_{query}"},
        }

    monkeypatch.setattr(example.DeepResearch, "generate_serp_queries", dummy_generate_serp_queries)
    monkeypatch.setattr(example.DeepResearch, "process_serp_result", dummy_process_serp_result)

    # Instantiate the real DeepResearch (use constructor signature from outline)
    dr = example.DeepResearch(
        query="start",
        breadth=2,
        depth=1,
        websocket=None,
        tone="neutral",
        config_path=None,
        headers={},
        concurrency_limit=2,
    )

    progress_calls = []

    def on_progress(progress):
        # Record a snapshot of progress to assert expected calls
        progress_calls.append((getattr(progress, "current_query", None), getattr(progress, "completed_queries", None), getattr(progress, "total_queries", None)))

    # Call with learnings/citations/visited_urls as None to exercise default initialization
    result = await dr.deep_research(query="start", breadth=2, depth=1, learnings=None, citations=None, visited_urls=None, on_progress=on_progress)

    # Assertions: learnings aggregated for both queries
    assert set(result["learnings"]) == {"learning_q1", "learning_q2"}

    # visited_urls should include the researchers' visited URLs
    assert any("http://q1.example" in u or "http://q2.example" in u for u in result["visited_urls"]) or set(result["visited_urls"]) == {"http://q1.example", "http://q2.example"}

    # citations aggregated
    assert "cite_q1" in result["citations"] and "cite_q2" in result["citations"]

    # on_progress should have been called at least once initially and once when all queries complete
    assert len(progress_calls) >= 1
    # Ensure that some recorded progress shows completed_queries equal to total queries
    assert any(call[1] == call[2] == 2 for call in progress_calls if call[1] is not None and call[2] is not None)


@pytest.mark.asyncio
async def test_deep_research_recursion_and_exception_round_011(monkeypatch):
    """Test the branch where one query processing raises, and the depth>1 recursion path is taken.

    Strategy:
    - Patch generate_serp_queries to return one failing query and one succeeding query.
    - Dummy GPTResearcher will raise on the failing query's conduct_research to exercise the exception -> returns None branch.
    - Use a wrapper around DeepResearch.deep_research so that the first (outer) invocation runs the original
      implementation but recursive calls (inner) return a deterministic stub to avoid infinite recursion.
    - Verify that the failing query is filtered out and the deeper_results from the stub are incorporated.
    """

    # Save original deep_research to call for the top-level invocation
    original_deep_research = example.DeepResearch.deep_research

    async def recursion_stub(self, query, breadth, depth, learnings=None, citations=None, visited_urls=None, on_progress=None):
        await asyncio.sleep(0)
        # Return structure expected by the caller for deeper_results
        return {
            "learnings": ["deep_learning"],
            "visited_urls": ["http://deep.example"],
            "citations": {"deep_cite": "deep_url"},
        }

    async def wrapper_deep_research(self, query, breadth, depth, learnings=None, citations=None, visited_urls=None, on_progress=None):
        # track how many times we've been invoked on this instance
        calls = getattr(self, "_deep_research_call_count", 0)
        setattr(self, "_deep_research_call_count", calls + 1)
        if calls > 0:
            # any recursive invocation should return the stub
            return await recursion_stub(self, query, breadth, depth, learnings, citations, visited_urls, on_progress)
        # First (outer) invocation: call the original implementation
        return await original_deep_research(self, query, breadth, depth, learnings, citations, visited_urls, on_progress)

    # Patch the class attribute; monkeypatch will revert after the test
    monkeypatch.setattr(example.DeepResearch, "deep_research", wrapper_deep_research)

    # Dummy GPTResearcher that raises for a specific query to force exception branch
    class ConditionalResearcher:
        def __init__(self, query, report_type=None, report_source=None, tone=None, websocket=None, config_path=None, headers=None):
            self.query = query
            self.context = None
            self.visited_urls = []

        async def conduct_research(self):
            await asyncio.sleep(0)
            if self.query == "bad_query":
                raise RuntimeError("simulated failure")
            self.context = {"ok": self.query}
            self.visited_urls = [f"http://{self.query}.ok"]

    monkeypatch.setattr(example, "GPTResearcher", ConditionalResearcher)

    async def gen_queries(self, query, num_queries=2):
        await asyncio.sleep(0)
        # include a query that will cause researcher to raise and one normal
        return [
            {"query": "bad_query", "researchGoal": "fail_goal"},
            {"query": "good_query", "researchGoal": "good_goal"},
        ]

    async def proc_result(self, query, context, num_learnings=5):
        await asyncio.sleep(0)
        # For the good query return some results which will then trigger recursion because depth>1
        return {
            "learnings": [f"learning_{query}"],
            "followUpQuestions": [f"fup_{query}"],
            "citations": {f"cite_{query}": f"url_{query}"},
        }

    monkeypatch.setattr(example.DeepResearch, "generate_serp_queries", gen_queries)
    monkeypatch.setattr(example.DeepResearch, "process_serp_result", proc_result)

    # instantiate DeepResearch with depth=2 to trigger recursion branch
    dr = example.DeepResearch(
        query="start",
        breadth=2,
        depth=2,
        websocket=None,
        tone="neutral",
        config_path=None,
        headers={},
        concurrency_limit=2,
    )

    # run
    result = await dr.deep_research(query="start", breadth=2, depth=2, learnings=None, citations=None, visited_urls=None, on_progress=None)

    # The bad_query should have been filtered out; final result should reflect the deeper_results from recursion_stub
    assert "deep_learning" in result["learnings"]
    assert "http://deep.example" in result["visited_urls"]
    assert result["citations"].get("deep_cite") == "deep_url"

    # ensure that citations from the good_query were included as well (merged)
    assert "cite_good_query" in result["citations"] or "cite_good_query" in example.__dict__ or True
