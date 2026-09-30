import asyncio
from types import SimpleNamespace
import pytest

from gpt_researcher.skills import researcher as researcher_module
from gpt_researcher.skills.researcher import ResearchConductor


# All generated test function names must end with _round_039

def _make_conductor(verbose=True):
    """Helper to create a ResearchConductor with a minimal researcher object."""
    researcher = SimpleNamespace(
        headers={"h": "v"},
        query_domains=["example.com"],
        websocket="fake-ws",
        cfg=SimpleNamespace(max_search_results_per_query=3),
        verbose=verbose,
    )
    return ResearchConductor(researcher)


def test_execute_mcp_research_with_results_round_039(monkeypatch):
    calls = []

    async def fake_stream_output(channel, tag, message, websocket):
        # record calls for assertion
        calls.append((channel, tag, message, websocket))

    # Patch the module-level stream_output used by the function under test
    monkeypatch.setattr(researcher_module, "stream_output", fake_stream_output)

    # Fake retriever that returns results from search()
    class FakeRetrieverWithResults:
        __name__ = "FakeRetrieverWithResults"

        def __init__(self, query, headers, query_domains, websocket, researcher):
            # capture inputs so we can assert they were passed correctly
            self.query = query
            self.headers = headers
            self.query_domains = query_domains
            self.websocket = websocket
            self.researcher = researcher

        def search(self, max_results=None):
            # deterministic non-empty result
            return [{"id": "r1", "q": self.query}]

    conductor = _make_conductor(verbose=True)

    # Run the async function synchronously for testing
    results = asyncio.run(conductor._execute_mcp_research(FakeRetrieverWithResults, "my-query"))

    # Oracle: function should return the results coming from retriever.search()
    assert results == [{"id": "r1", "q": "my-query"}]

    # Oracle: stream_output should have been called for stage1 and completion (verbose True)
    tags = [call[1] for call in calls]
    assert "mcp_retrieval_stage1" in tags
    assert "mcp_research_complete" in tags


def test_execute_mcp_research_no_results_round_039(monkeypatch):
    calls = []

    async def fake_stream_output(channel, tag, message, websocket):
        calls.append((channel, tag, message, websocket))

    monkeypatch.setattr(researcher_module, "stream_output", fake_stream_output)

    class FakeRetrieverNoResults:
        __name__ = "FakeRetrieverNoResults"

        def __init__(self, query, headers, query_domains, websocket, researcher):
            self.query = query

        def search(self, max_results=None):
            # deterministic empty result
            return []

    conductor = _make_conductor(verbose=True)
    results = asyncio.run(conductor._execute_mcp_research(FakeRetrieverNoResults, "no-result-query"))

    # Oracle: empty list returned when retriever.search() returns falsy/empty
    assert results == []

    # Oracle: stream_output should have been called for stage1 and no-results (verbose True)
    tags = [call[1] for call in calls]
    assert "mcp_retrieval_stage1" in tags
    assert "mcp_no_results" in tags


def test_execute_mcp_research_exception_round_039(monkeypatch):
    calls = []

    async def fake_stream_output(channel, tag, message, websocket):
        calls.append((channel, tag, message, websocket))

    monkeypatch.setattr(researcher_module, "stream_output", fake_stream_output)

    class BadRetriever:
        __name__ = "BadRetriever"

        def __init__(self, *args, **kwargs):
            # Raise during instantiation to simulate runtime error in retriever construction
            raise RuntimeError("instantiation failed")

    conductor = _make_conductor(verbose=True)
    results = asyncio.run(conductor._execute_mcp_research(BadRetriever, "err-query"))

    # Oracle: on exception the function should return an empty list
    assert results == []

    # Oracle: since verbose True, an error stream_output call should have been made
    tags = [call[1] for call in calls]
    assert "mcp_research_error" in tags
