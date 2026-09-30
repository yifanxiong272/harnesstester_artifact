import asyncio
from types import SimpleNamespace
import pytest

import gpt_researcher.skills.researcher as researcher_mod
from gpt_researcher.skills.researcher import ResearchConductor

# Helper to create a minimal researcher stub expected by ResearchConductor
class DummyCfg:
    def __init__(self, max_search_results_per_query=10):
        self.max_search_results_per_query = max_search_results_per_query


def make_researcher_stub(verbose=True):
    return SimpleNamespace(
        headers={"Authorization": "none"},
        query_domains=["example.com"],
        websocket="dummy_ws",
        verbose=verbose,
        cfg=DummyCfg(max_search_results_per_query=10),
    )


# Test 1: Retriever without a search method -> should return [] and not raise
def test_retriever_no_search_round_021():
    class NoSearchRetriever:
        # Name intentionally does NOT include 'mcp' to be non-MCP retriever
        def __init__(self, *args, **kwargs):
            # accept the expected kwargs but do nothing
            self.args = args
            self.kwargs = kwargs

    researcher = make_researcher_stub(verbose=False)
    conductor = ResearchConductor(researcher)

    # Call the async method synchronously via asyncio.run
    results = asyncio.run(conductor._search(NoSearchRetriever, "query1"))

    # Oracle: non-mcp retriever without search method should return an empty list
    assert results == []


# Test 2: MCP retriever that returns no results -> triggers mcp_no_results stream_output
def test_mcp_retriever_no_results_round_021(monkeypatch):
    calls = []

    async def fake_stream_output(channel, event, message, websocket):
        # capture calls for assertion
        calls.append((channel, event, message, websocket))

    # Patch the module-level stream_output used by ResearchConductor._search
    monkeypatch.setattr(researcher_mod, "stream_output", fake_stream_output)

    class MCPRetriever:
        # name contains 'MCPRetriever' so is_mcp_retriever becomes True
        def __init__(self, *args, **kwargs):
            pass

        def search(self, *, max_results=None):
            # return empty list to trigger 'no results' branch
            return []

    researcher = make_researcher_stub(verbose=True)
    conductor = ResearchConductor(researcher)

    results = asyncio.run(conductor._search(MCPRetriever, "no-results-query"))

    # Oracle: should return [] and the stream_output must be called for no-results
    assert results == []

    # Find any call where event == 'mcp_no_results'
    events = [c[1] for c in calls]
    assert "mcp_no_results" in events


# Test 3: MCP retriever that returns multiple results (>3) -> logs first 3 and notices extra
def test_mcp_retriever_with_results_many_round_021(monkeypatch):
    calls = []

    async def fake_stream_output(channel, event, message, websocket):
        calls.append((channel, event, message, websocket))

    monkeypatch.setattr(researcher_mod, "stream_output", fake_stream_output)

    class MCPRetriever:
        def __init__(self, *args, **kwargs):
            pass

        def search(self, *, max_results=None):
            # produce 5 fake results to exercise the '... and N more MCP results' branch
            return [
                {"title": f"Title {i}", "href": f"http://example.com/{i}", "body": "x" * (10 + i)}
                for i in range(5)
            ]

    researcher = make_researcher_stub(verbose=True)
    conductor = ResearchConductor(researcher)

    results = asyncio.run(conductor._search(MCPRetriever, "many-results-query"))

    # Oracle: returned results should be the same list of dicts and stream_output should have been used
    assert isinstance(results, list) and len(results) == 5

    # Ensure we saw both initial MCP retrieval notification and MCP results notification
    events = [c[1] for c in calls]
    assert "mcp_retrieval" in events
    assert "mcp_results" in events


# Test 4: Retriever whose constructor raises -> triggers exception handling and mcp_error
def test_exception_during_instantiation_round_021(monkeypatch):
    calls = []

    async def fake_stream_output(channel, event, message, websocket):
        calls.append((channel, event, message, websocket))

    monkeypatch.setattr(researcher_mod, "stream_output", fake_stream_output)

    class BrokenMCPRetriever:
        # Class name includes 'MCPRetriever' so treated as MCP retriever
        def __init__(self, *args, **kwargs):
            raise RuntimeError("instantiation failed")

    researcher = make_researcher_stub(verbose=True)
    conductor = ResearchConductor(researcher)

    results = asyncio.run(conductor._search(BrokenMCPRetriever, "bad-init"))

    # Oracle: on exception, _search should return [] and trigger mcp_error when MCP & verbose
    assert results == []
    events = [c[1] for c in calls]
    assert "mcp_error" in events
