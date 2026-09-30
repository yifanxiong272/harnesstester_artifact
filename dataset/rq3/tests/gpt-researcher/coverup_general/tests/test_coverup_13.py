# file: gpt_researcher/skills/researcher.py:580-652
# asked: {"lines": [591, 593, 595, 598, 599, 600, 601, 602, 603, 606, 607, 608, 609, 610, 611, 615, 616, 619, 620, 621, 623, 624, 625, 626, 627, 628, 631, 633, 634, 635, 636, 637, 638, 639, 641, 643, 644, 645, 646, 647, 648, 649, 650, 652], "branches": [[606, 607], [606, 615], [619, 620], [619, 633], [623, 624], [623, 631], [634, 635], [634, 641], [645, 646], [645, 652]]}
# gained: {"lines": [591, 593, 595, 598, 599, 600, 601, 602, 603, 606, 607, 608, 609, 610, 611, 615, 616, 619, 620, 621, 623, 624, 625, 626, 627, 628, 631, 633, 634, 635, 636, 637, 638, 639, 641, 643, 644, 645, 646, 647, 648, 649, 650, 652], "branches": [[606, 607], [619, 620], [619, 633], [623, 624], [634, 635], [645, 646]]}

import pytest
import types

import gpt_researcher.skills.researcher as researcher_module
from gpt_researcher.skills.researcher import ResearchConductor


class DummyCfg:
    def __init__(self, max_search_results_per_query=5):
        self.max_search_results_per_query = max_search_results_per_query


class DummyResearcher:
    def __init__(self, *, headers=None, query_domains=None, websocket=None, verbose=False, max_results=5):
        self.headers = headers or {}
        self.query_domains = query_domains or []
        self.websocket = websocket
        self.verbose = verbose
        self.cfg = DummyCfg(max_results)


@pytest.mark.asyncio
async def test_execute_mcp_research_returns_results_and_streams_when_verbose_true(monkeypatch):
    calls = []

    async def fake_stream_output(channel, key, message, websocket):
        # record calls for assertions
        calls.append((channel, key, message, websocket))

    # Patch the module-level stream_output used by ResearchConductor
    monkeypatch.setattr(researcher_module, "stream_output", fake_stream_output)

    # Define a retriever class whose search returns results
    class RetrieverWithResults:
        def __init__(self, query, headers, query_domains, websocket, researcher):
            # store to assert proper construction if needed
            self.query = query
            self.headers = headers
            self.query_domains = query_domains
            self.websocket = websocket
            self.researcher = researcher

        def search(self, max_results):
            # should be called with researcher's cfg.max_search_results_per_query
            assert max_results == 3
            return ["result1", "result2"]

    # Prepare researcher object and conductor
    dummy_res = DummyResearcher(headers={"h": "v"}, query_domains=["example.com"], websocket="ws1", verbose=True, max_results=3)
    conductor = ResearchConductor(dummy_res)

    results = await conductor._execute_mcp_research(RetrieverWithResults, "test query")

    # Verify returned results and that stream_output was called for stage1 and completion
    assert results == ["result1", "result2"]
    # Two stream_output calls: stage1 and mcp_research_complete
    assert len(calls) == 2
    assert calls[0][1] == "mcp_retrieval_stage1"
    assert "Stage 1" in calls[0][2] or "Stage 1: Selecting" in calls[0][2] or "Selecting" in calls[0][2]
    assert calls[0][3] == "ws1"
    assert calls[1][1] == "mcp_research_complete"
    assert "MCP research completed" in calls[1][2] or "intelligent results" in calls[1][2]
    assert calls[1][3] == "ws1"


@pytest.mark.asyncio
async def test_execute_mcp_research_no_results_streams_when_verbose_true(monkeypatch):
    calls = []

    async def fake_stream_output(channel, key, message, websocket):
        calls.append((channel, key, message, websocket))

    monkeypatch.setattr(researcher_module, "stream_output", fake_stream_output)

    class RetrieverNoResults:
        def __init__(self, query, headers, query_domains, websocket, researcher):
            self.query = query

        def search(self, max_results):
            return []  # No results branch

    dummy_res = DummyResearcher(headers={}, query_domains=[], websocket="ws2", verbose=True, max_results=2)
    conductor = ResearchConductor(dummy_res)

    results = await conductor._execute_mcp_research(RetrieverNoResults, "empty query")

    assert results == []
    # Should have stage1 and mcp_no_results calls
    assert len(calls) == 2
    assert calls[0][1] == "mcp_retrieval_stage1"
    assert calls[1][1] == "mcp_no_results"
    assert calls[1][3] == "ws2"


@pytest.mark.asyncio
async def test_execute_mcp_research_handles_exception_and_streams_error(monkeypatch):
    calls = []

    async def fake_stream_output(channel, key, message, websocket):
        calls.append((channel, key, message, websocket))

    monkeypatch.setattr(researcher_module, "stream_output", fake_stream_output)

    class RetrieverRaises:
        def __init__(self, query, headers, query_domains, websocket, researcher):
            # constructed fine
            pass

        def search(self, max_results):
            raise RuntimeError("boom error in search")

    dummy_res = DummyResearcher(headers={}, query_domains=[], websocket="ws3", verbose=True, max_results=4)
    conductor = ResearchConductor(dummy_res)

    results = await conductor._execute_mcp_research(RetrieverRaises, "explode")

    # On exception, the method should return empty list and stream an error message
    assert results == []
    # Should have stage1 and error call (stage1 before exception handling)
    # Depending on where exception occurred, stage1 might have been called (it is called before search)
    # So check that at least one call contains the error key
    error_calls = [c for c in calls if c[1] == "mcp_research_error"]
    assert len(error_calls) == 1
    # The error message should include the exception text
    assert "boom error in search" in error_calls[0][2]
    assert error_calls[0][3] == "ws3"
