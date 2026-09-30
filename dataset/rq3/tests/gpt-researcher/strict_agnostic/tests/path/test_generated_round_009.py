import asyncio
import pytest
from gpt_researcher.skills.researcher import ResearchConductor


class FakeResearcher:
    def __init__(self, retrievers, verbose, websocket, report_type):
        self.retrievers = retrievers
        self.verbose = verbose
        self.websocket = websocket
        self.report_type = report_type


class MyMCPRetriever:
    """Name intentionally includes 'MCP' so __name__.lower() contains 'mcpretriever' when lowercased."""
    pass


def _make_recorder(monkeypatch):
    calls = []

    async def recorder_stream(kind, tag, message, websocket, *args, **kwargs):
        # record the tuple of (kind, tag, message, websocket, extra args) for assertions
        calls.append((kind, tag, message, websocket, args))

    monkeypatch.setattr("gpt_researcher.skills.researcher.stream_output", recorder_stream)
    return calls


def test_mcp_disabled_and_exception_round_009(monkeypatch):
    """
    - Simulate MCP present, strategy == 'disabled', verbose True.
    - plan_research returns one sub-query, _process_sub_query raises -> triggers exception path in gather.
    - Assert function returns [] and that stream_output was called for mcp_disabled and subqueries.
    """
    calls = _make_recorder(monkeypatch)

    researcher = FakeResearcher(retrievers=[MyMCPRetriever], verbose=True, websocket=None, report_type="normal")
    rc = ResearchConductor(researcher)

    # Force MCP strategy to 'disabled'
    monkeypatch.setattr(rc, "_get_mcp_strategy", lambda: "disabled")
    rc._mcp_results_cache = None

    # plan_research is awaited as plan_research(query, query_domains) - provide matching async function
    async def plan_research(query, query_domains):
        return ["sub_one"]

    monkeypatch.setattr(rc, "plan_research", plan_research)

    # _process_sub_query will raise to exercise the exception handling branch
    async def process_sub_query(sub_query, scraped_data, query_domains):
        raise RuntimeError("simulated sub-query failure")

    monkeypatch.setattr(rc, "_process_sub_query", process_sub_query)

    # Run the async function synchronously for deterministic test behavior
    result = asyncio.run(rc._get_context_by_web_search("some query", scraped_data=None, query_domains=None))

    # Expect the exception to be caught and an empty list returned
    assert result == []

    # Validate that stream_output was used for MCP disabled logging and subqueries logging
    tags = [c[1] for c in calls]
    assert "mcp_disabled" in tags, f"expected 'mcp_disabled' in stream_output tags, got: {tags}"
    assert "subqueries" in tags, f"expected 'subqueries' in stream_output tags, got: {tags}"


def test_mcp_fast_and_combined_context_round_009(monkeypatch):
    """
    - Simulate MCP present, strategy == 'fast'.
    - _execute_mcp_research_for_queries returns a deterministic list to be cached.
    - plan_research returns one sub-query; _process_sub_query returns string results.
    - Assert combined context string returned and _mcp_results_cache set.
    """
    calls = _make_recorder(monkeypatch)

    researcher = FakeResearcher(retrievers=[MyMCPRetriever], verbose=True, websocket=None, report_type="normal")
    rc = ResearchConductor(researcher)

    # Force MCP strategy to 'fast' (synchronous getter)
    monkeypatch.setattr(rc, "_get_mcp_strategy", lambda: "fast")
    rc._mcp_results_cache = None

    # Async MCP execution returns a deterministic list
    async def exec_mcp(queries, retrievers):
        # Return a predictable mcp context list
        return ["mcp_context_entry_1", "mcp_context_entry_2"]

    monkeypatch.setattr(rc, "_execute_mcp_research_for_queries", exec_mcp)

    async def plan_research(query, query_domains):
        # Return a single generated sub-query to be processed
        return ["subq1"]

    monkeypatch.setattr(rc, "plan_research", plan_research)

    async def process_sub_query(sub_query, scraped_data, query_domains):
        # deterministic content for each sub_query
        return f"content_for_{sub_query}"

    monkeypatch.setattr(rc, "_process_sub_query", process_sub_query)

    # Execute the target function
    result = asyncio.run(rc._get_context_by_web_search("orig_query", scraped_data=[], query_domains=[]))

    # The returned value should be a combined string of non-empty results
    assert isinstance(result, str), "expected a combined context string when sub-queries return content"
    assert "content_for_subq1" in result

    # MCP results should have been cached from the fast path
    assert rc._mcp_results_cache == ["mcp_context_entry_1", "mcp_context_entry_2"]

    # Validate that stream_output recorded an mcp-related optimization message and subqueries
    tags = [c[1] for c in calls]
    assert "mcp_optimization" in tags, f"expected 'mcp_optimization' in stream_output tags, got: {tags}"
    assert "subqueries" in tags
