import asyncio
import types
from types import SimpleNamespace
import pytest

from gpt_researcher.skills import researcher as researcher_mod
from gpt_researcher.skills.researcher import ResearchConductor

# Helper async stub to capture calls
class AsyncRecorder:
    def __init__(self):
        self.calls = []

    async def __call__(self, *args, **kwargs):
        # record call arguments for assertions
        self.calls.append((args, kwargs))
        # return a deterministic placeholder
        return None


def make_conductor(monkeypatch, *, retrievers=None, verbose=True, report_type="report"):
    """
    Create a ResearchConductor instance without invoking its __init__ and configure
    the minimal attributes needed by _get_context_by_web_search.
    """
    # instantiate without __init__ to avoid side effects
    c = object.__new__(ResearchConductor)

    # attach a simple logger that has info/warning/error methods
    import logging

    c.logger = logging.getLogger(f"test_researcher_{id(c)}")

    # researcher object expected by the method
    if retrievers is None:
        retrievers = []
    c.researcher = SimpleNamespace(
        retrievers=retrievers,
        verbose=verbose,
        websocket=None,
        report_type=report_type,
    )

    # initial MCP cache state
    c._mcp_results_cache = None

    # Provide synchronous _get_mcp_strategy default; tests override as needed
    c._get_mcp_strategy = lambda: "disabled"

    # Provide async stubs for methods awaited in the method; include 'self' in signatures
    async def _execute_mcp_research_for_queries(self, queries, mcp_retrievers):
        # deterministic return: list with a single string entry per query
        return [f"mcp_result_for:{q}" for q in queries]

    async def plan_research(self, query, query_domains):
        # default: no sub-queries (tests may patch to other values)
        return []

    async def _process_sub_query(self, sub_query, scraped_data, query_domains):
        # default: return empty string to simulate no useful content
        return ""

    c._execute_mcp_research_for_queries = types.MethodType(_execute_mcp_research_for_queries, c)
    c.plan_research = types.MethodType(plan_research, c)
    c._process_sub_query = types.MethodType(_process_sub_query, c)

    return c


@pytest.mark.asyncio
async def test_get_context_web_search_no_mcp_retrievers_combines_context_round_009(monkeypatch):
    """
    Case: no MCP retrievers present -> skip MCP logic. plan_research returns empty list,
    so the original query is appended and processed. The _process_sub_query returns
    a non-empty string and the method should return the combined string.
    Covers: lines where scraped_data/query_domains defaulting happens and the
    path where mcp_retrievers is empty, sub-queries appended with original query,
    and successful combine + return of string.
    """
    recorder = AsyncRecorder()
    monkeypatch.setattr(researcher_mod, "stream_output", recorder)

    # Create conductor with no retrievers
    c = make_conductor(monkeypatch, retrievers=[], verbose=True, report_type="report")

    # Patch plan_research to return [] (so original query gets appended)
    async def plan_research(self, query, query_domains):
        return []

    async def process_sub_query(self, sub_query, scraped_data, query_domains):
        # return a non-empty string to be combined
        return f"result_for:{sub_query}"

    c.plan_research = types.MethodType(plan_research, c)
    c._process_sub_query = types.MethodType(process_sub_query, c)

    res = await c._get_context_by_web_search("my query")

    # Should have returned the combined single result string
    assert res == "result_for:my query"

    # stream_output should have been called when researcher.verbose is True for subqueries
    # The last recorded call should contain the 'subqueries' identifier
    assert any(call[0][1] == "subqueries" for call in recorder.calls), "expected subqueries stream_output call"


@pytest.mark.asyncio
async def test_get_context_web_search_mcp_disabled_returns_empty_round_009(monkeypatch):
    """
    Case: MCP retrievers exist and strategy is 'disabled'. When researcher.verbose is True,
    stream_output should be invoked with 'mcp_disabled'. If sub-queries produce no content,
    method should return an empty list ([]) as per the code path.
    """
    recorder = AsyncRecorder()
    monkeypatch.setattr(researcher_mod, "stream_output", recorder)

    # create a dummy retriever type whose __name__ contains 'mcpretriever'
    class DummyMCPRetriever:
        pass

    c = make_conductor(monkeypatch, retrievers=[DummyMCPRetriever], verbose=True, report_type="report")

    # force strategy to 'disabled'
    c._get_mcp_strategy = lambda: "disabled"

    # plan_research returns [] -> original query appended
    async def plan_research(self, query, query_domains):
        return []

    # process_sub_query returns empty string -> filtered out
    async def process_sub_query(self, sub_query, scraped_data, query_domains):
        return ""

    c.plan_research = types.MethodType(plan_research, c)
    c._process_sub_query = types.MethodType(process_sub_query, c)

    res = await c._get_context_by_web_search("another query")

    # When there is no context produced, the function returns an empty list
    assert res == [], "expected empty list when no sub-query produced content"

    # Verify that an MCP-disabled stream output call was issued
    assert any(call[0][1] == "mcp_disabled" for call in recorder.calls), "expected mcp_disabled stream_output call"


@pytest.mark.asyncio
async def test_get_context_web_search_mcp_fast_caches_results_round_009(monkeypatch):
    """
    Case: MCP retrievers exist and strategy is 'fast'. _execute_mcp_research_for_queries should
    be awaited, its return value cached on self._mcp_results_cache, and stream_output called
    with 'mcp_optimization' when verbose.
    """
    recorder = AsyncRecorder()
    monkeypatch.setattr(researcher_mod, "stream_output", recorder)

    class DummyMCPRetriever:
        pass

    c = make_conductor(monkeypatch, retrievers=[DummyMCPRetriever], verbose=True, report_type="report")

    # set strategy to 'fast'
    c._get_mcp_strategy = lambda: "fast"

    # Replace the MCP execution to return a known deterministic list (include self param)
    async def fake_execute_mcp(self, queries, mcp_retrievers):
        # Return a deterministic small list irrespective of inputs
        return ["mcpcached1", "mcpcached2"]

    c._execute_mcp_research_for_queries = types.MethodType(fake_execute_mcp, c)

    # plan_research returns [] so original query appended
    async def plan_research(self, query, query_domains):
        return []

    # process_sub_query returns one piece of content
    async def process_sub_query(self, sub_query, scraped_data, query_domains):
        return "web_content"

    c.plan_research = types.MethodType(plan_research, c)
    c._process_sub_query = types.MethodType(process_sub_query, c)

    res = await c._get_context_by_web_search("fast query")

    # Should return the web_content combined
    assert res == "web_content"

    # Cache should be set to the fake_execute_mcp result
    assert c._mcp_results_cache == ["mcpcached1", "mcpcached2"]

    # Ensure that stream_output was called for mcp_optimization (fast path)
    assert any(call[0][1] == "mcp_optimization" for call in recorder.calls), "expected mcp_optimization stream_output call"


@pytest.mark.asyncio
async def test_get_context_web_search_mcp_deep_does_not_cache_round_009(monkeypatch):
    """
    Case: MCP retrievers exist and strategy is 'deep'. The code path should call stream_output
    for 'mcp_comprehensive' when verbose, and should NOT set the _mcp_results_cache.
    This verifies the 'deep' branch which logs and defers caching.
    """
    recorder = AsyncRecorder()
    monkeypatch.setattr(researcher_mod, "stream_output", recorder)

    class DummyMCPRetriever:
        pass

    c = make_conductor(monkeypatch, retrievers=[DummyMCPRetriever], verbose=True, report_type="report")

    # set strategy to 'deep'
    c._get_mcp_strategy = lambda: "deep"

    # Ensure that if executed, the MCP executor would return something (but deep should not cache)
    async def fake_execute_mcp(self, queries, mcp_retrievers):
        return ["mcpcached_for_deep"]

    c._execute_mcp_research_for_queries = types.MethodType(fake_execute_mcp, c)

    # plan_research returns single sub-query that yields content
    async def plan_research(self, query, query_domains):
        return ["subq1"]

    async def process_sub_query(self, sub_query, scraped_data, query_domains):
        return "deep_content"

    c.plan_research = types.MethodType(plan_research, c)
    c._process_sub_query = types.MethodType(process_sub_query, c)

    res = await c._get_context_by_web_search("deep query")

    # Should return combined content from sub-query
    assert res == "deep_content"

    # _mcp_results_cache must remain None for deep strategy
    assert c._mcp_results_cache is None

    # stream_output should have been called with 'mcp_comprehensive'
    assert any(call[0][1] == "mcp_comprehensive" for call in recorder.calls), "expected mcp_comprehensive stream_output call"
