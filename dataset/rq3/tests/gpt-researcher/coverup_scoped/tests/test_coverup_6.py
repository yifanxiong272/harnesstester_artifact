# file: gpt_researcher/skills/researcher.py:836-924
# asked: {"lines": [847, 848, 850, 852, 854, 855, 856, 857, 858, 859, 863, 864, 865, 866, 867, 868, 872, 873, 874, 878, 879, 880, 883, 884, 885, 886, 887, 888, 889, 893, 894, 895, 896, 897, 899, 900, 902, 903, 904, 905, 906, 907, 908, 911, 913, 914, 915, 916, 917, 918, 919, 920, 921, 922, 924], "branches": [[863, 864], [863, 872], [872, 873], [872, 913], [878, 879], [878, 902], [883, 884], [883, 911], [884, 885], [884, 893], [893, 894], [893, 899], [899, 900], [899, 911], [903, 904], [903, 911], [917, 918], [917, 924]]}
# gained: {"lines": [847, 848, 850, 852, 854, 855, 856, 857, 858, 859, 863, 864, 865, 866, 867, 868, 872, 873, 874, 878, 879, 880, 883, 884, 885, 886, 887, 888, 889, 893, 894, 895, 896, 897, 899, 900, 911, 913, 914, 915, 916, 917, 918, 919, 920, 921, 922, 924], "branches": [[863, 864], [863, 872], [872, 873], [872, 913], [878, 879], [883, 884], [883, 911], [884, 885], [893, 894], [893, 899], [899, 900], [917, 918]]}

import pytest

import types

import gpt_researcher.skills.researcher as researcher_mod


class FakeLogger:
    def __init__(self):
        self.info_calls = []
        self.error_calls = []

    def info(self, msg):
        self.info_calls.append(msg)

    def error(self, msg):
        self.error_calls.append(msg)


class FakeCFG:
    def __init__(self, max_search_results_per_query=5):
        self.max_search_results_per_query = max_search_results_per_query


class FakeResearcher:
    def __init__(self, headers=None, query_domains=None, websocket=None, verbose=False, cfg=None):
        self.headers = headers or {}
        self.query_domains = query_domains or []
        self.websocket = websocket
        self.verbose = verbose
        self.cfg = cfg or FakeCFG()


@pytest.mark.asyncio
async def test_non_mcp_search_returns_results(monkeypatch):
    # Arrange
    ResearchConductor = researcher_mod.ResearchConductor
    conductor = object.__new__(ResearchConductor)
    conductor.logger = FakeLogger()
    conductor.researcher = FakeResearcher(headers={"h": "v"}, query_domains=["example.com"], websocket=None, verbose=False,
                                         cfg=FakeCFG(max_search_results_per_query=3))

    class SimpleRetriever:
        def __init__(self, query, headers, query_domains, websocket=None, researcher=None):
            # ensure parameters passed correctly
            self.query = query
            self.headers = headers
            self.query_domains = query_domains
            self.websocket = websocket
            self.researcher = researcher

        def search(self, max_results=None):
            return [{"title": "T1", "href": "http://u", "body": "abc"}]

    # patch stream_output to ensure it would not be called accidentally
    async def fake_stream_output(*args, **kwargs):
        raise AssertionError("stream_output should not be called for non-MCP retriever")

    monkeypatch.setattr(researcher_mod, "stream_output", fake_stream_output)

    # Act
    results = await conductor._search(SimpleRetriever, "some query")

    # Assert
    assert isinstance(results, list)
    assert results == [{"title": "T1", "href": "http://u", "body": "abc"}]
    # logger should have recorded receiving results
    assert any("Received 1 results from SimpleRetriever" in m for m in conductor.logger.info_calls)


@pytest.mark.asyncio
async def test_non_mcp_no_search_method(monkeypatch):
    # Arrange
    ResearchConductor = researcher_mod.ResearchConductor
    conductor = object.__new__(ResearchConductor)
    conductor.logger = FakeLogger()
    conductor.researcher = FakeResearcher(cfg=FakeCFG())

    class NoSearchRetriever:
        def __init__(self, query, headers, query_domains, websocket=None, researcher=None):
            pass

    async def fake_stream_output(*args, **kwargs):
        raise AssertionError("stream_output should not be called for non-MCP retriever")

    monkeypatch.setattr(researcher_mod, "stream_output", fake_stream_output)

    # Act
    results = await conductor._search(NoSearchRetriever, "q")

    # Assert
    assert results == []
    assert any("does not have a search method" in e for e in conductor.logger.error_calls)


@pytest.mark.asyncio
async def test_mcp_retriever_with_many_results_and_verbose(monkeypatch):
    # Arrange
    ResearchConductor = researcher_mod.ResearchConductor
    conductor = object.__new__(ResearchConductor)
    conductor.logger = FakeLogger()
    # verbose True so stream_output should be awaited
    cfg = FakeCFG(max_search_results_per_query=10)
    researcher = FakeResearcher(headers={}, query_domains=[], websocket="ws://socket", verbose=True, cfg=cfg)
    conductor.researcher = researcher

    # create MCP retriever (name must include 'mcpretriever' case-insensitive)
    class MCPRetriever:
        def __init__(self, query, headers, query_domains, websocket=None, researcher=None):
            # ensure the websocket and researcher are passed for MCP retriever
            self.query = query
            self.headers = headers
            self.web = websocket
            self.researcher = researcher

        def search(self, max_results=None):
            # return more than 3 results to trigger the "... and X more" branch
            return [
                {"title": "t1", "href": "u1", "body": "body1"},
                {"title": "t2", "href": "u2", "body": "body2"},
                {"title": "t3", "href": "u3", "body": "body3"},
                {"title": "t4", "href": "u4", "body": "body4"},
                {"title": "t5", "href": "u5", "body": "body5"},
            ]

    # capture stream_output calls
    stream_calls = []

    async def fake_stream_output(stream_type, event, message, websocket):
        stream_calls.append((stream_type, event, message, websocket))
        return None

    monkeypatch.setattr(researcher_mod, "stream_output", fake_stream_output)

    # Act
    results = await conductor._search(MCPRetriever, "mcp query")

    # Assert
    assert isinstance(results, list)
    assert len(results) == 5
    # stream_output should have been called for retrieval and results
    assert any(call[1] == "mcp_retrieval" for call in stream_calls)
    assert any(call[1] == "mcp_results" for call in stream_calls)
    # logger should include the "... and 2 more MCP results" message
    assert any("... and 2 more MCP results" in m for m in conductor.logger.info_calls)
    # logger should have MCP result lines for first three
    assert any("MCP result 1:" in m for m in conductor.logger.info_calls)
    assert any("MCP result 2:" in m for m in conductor.logger.info_calls)
    assert any("MCP result 3:" in m for m in conductor.logger.info_calls)


@pytest.mark.asyncio
async def test_mcp_retriever_init_raises_and_stream_error_called(monkeypatch):
    # Arrange
    ResearchConductor = researcher_mod.ResearchConductor
    conductor = object.__new__(ResearchConductor)
    conductor.logger = FakeLogger()
    researcher = FakeResearcher(headers={}, query_domains=[], websocket="ws://socket", verbose=True, cfg=FakeCFG())
    conductor.researcher = researcher

    class MCPRetrieverError:
        def __init__(self, query, headers, query_domains, websocket=None, researcher=None):
            raise ValueError("init boom")

    stream_calls = []

    async def fake_stream_output(stream_type, event, message, websocket):
        stream_calls.append((stream_type, event, message, websocket))
        return None

    monkeypatch.setattr(researcher_mod, "stream_output", fake_stream_output)

    # Act
    results = await conductor._search(MCPRetrieverError, "problem query")

    # Assert: should return empty list on exception
    assert results == []
    # logger.error should contain the error message
    assert any("Error searching with MCPRetrieverError" in e for e in conductor.logger.error_calls)
    # stream_output should have been called for mcp_error
    assert any(call[1] == "mcp_error" and "Error retrieving information" in call[2] for call in stream_calls)
