import types
import pytest

from gpt_researcher.skills import researcher as researcher_mod
from gpt_researcher.skills.researcher import ResearchConductor


class FakeLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg):
        # ensure deterministic string handling
        self.infos.append(str(msg))

    def error(self, msg):
        self.errors.append(str(msg))


class AsyncStreamCapture:
    def __init__(self):
        self.calls = []

    async def __call__(self, category, etype, message, websocket):
        # record exactly what was passed
        self.calls.append((category, etype, str(message), websocket))
        # No external side effects
        return None


@pytest.mark.asyncio
async def test_mcp_retriever_with_many_results_round_021(monkeypatch):
    """
    Exercise MCP retriever path where verbose=True and more than 3 results are returned.
    Asserts: returned results list, stream_output called for retrieval and results, logger info contains expected messages.
    """
    # Prepare stream_output stub and patch into module where function resolves
    stream_capture = AsyncStreamCapture()
    monkeypatch.setattr(researcher_mod, "stream_output", stream_capture)

    # Fake researcher state used by the method
    fake_researcher = types.SimpleNamespace(
        headers={"h": "v"},
        query_domains=["example.com"],
        websocket="fake_ws",
        verbose=True,
        cfg=types.SimpleNamespace(max_search_results_per_query=10),
    )

    fake_logger = FakeLogger()
    fake_self = types.SimpleNamespace(logger=fake_logger, researcher=fake_researcher)

    # Define an MCP retriever class (class name lower contains 'mcpretriever')
    class McPRetriever:
        def __init__(self, query=None, headers=None, query_domains=None, websocket=None, researcher=None):
            # record that websocket and researcher were passed for MCP retriever
            self.kwargs = dict(query=query, headers=headers, query_domains=query_domains, websocket=websocket, researcher=researcher)

        def search(self, max_results=None):
            # produce 5 results so we exercise the >3 branch and first-3 logging
            return [
                {"title": "T1", "href": "http://a/1", "body": "body1"},
                {"title": "T2", "href": "http://a/2", "body": "body2"},
                {"title": "T3", "href": "http://a/3", "body": "body3"},
                {"title": "T4", "href": "http://a/4", "body": "body4"},
                {"title": "T5", "href": "http://a/5", "body": "body5"},
            ]

    # Call the function-under-test
    results = await ResearchConductor._search(fake_self, McPRetriever, "my query")

    # Assertions: results returned and correct length
    assert isinstance(results, list) and len(results) == 5

    # stream_output should have been called twice: mcp_retrieval and mcp_results
    assert len(stream_capture.calls) == 2
    first_call = stream_capture.calls[0]
    second_call = stream_capture.calls[1]
    assert first_call[0] == "logs" and first_call[1] == "mcp_retrieval"
    assert "Consulting MCP server(s) for information on: my query" in first_call[2]
    assert second_call[0] == "logs" and second_call[1] == "mcp_results"
    assert "Retrieved 5 results from MCP server" in second_call[2]

    # Logger should have info about received results and MCP result entries + the trailing message about additional results
    info_text = "\n".join(fake_logger.infos)
    assert "Received 5 results" in info_text
    assert "MCP result 1: 'T1' from http://a/1 (5 chars)" in info_text
    assert "... and 2 more MCP results" in info_text


@pytest.mark.asyncio
async def test_non_mcp_retriever_no_results_round_021(monkeypatch):
    """
    Non-MCP retriever returning empty list -> should log no results and not call stream_output.
    """
    stream_capture = AsyncStreamCapture()
    monkeypatch.setattr(researcher_mod, "stream_output", stream_capture)

    fake_researcher = types.SimpleNamespace(
        headers={},
        query_domains=[],
        websocket=None,
        verbose=False,  # not verbose so no MCP-related streaming even if detection were true
        cfg=types.SimpleNamespace(max_search_results_per_query=5),
    )
    fake_logger = FakeLogger()
    fake_self = types.SimpleNamespace(logger=fake_logger, researcher=fake_researcher)

    class NormalRetriever:
        def __init__(self, query=None, headers=None, query_domains=None, websocket=None, researcher=None):
            pass

        def search(self, max_results=None):
            return []

    results = await ResearchConductor._search(fake_self, NormalRetriever, "something")
    assert results == []

    # No stream_output should have been invoked for non-MCP path
    assert stream_capture.calls == []

    # Logger should indicate no results returned
    assert any("No results returned" in m for m in fake_logger.infos)


@pytest.mark.asyncio
async def test_retriever_without_search_round_021(monkeypatch):
    """
    Retriever instance has no 'search' attribute -> should error-log and return empty list.
    """
    # ensure stream_output not to be called inadvertently
    stream_capture = AsyncStreamCapture()
    monkeypatch.setattr(researcher_mod, "stream_output", stream_capture)

    fake_researcher = types.SimpleNamespace(
        headers={},
        query_domains=[],
        websocket=None,
        verbose=False,
        cfg=types.SimpleNamespace(max_search_results_per_query=5),
    )
    fake_logger = FakeLogger()
    fake_self = types.SimpleNamespace(logger=fake_logger, researcher=fake_researcher)

    class NoSearchRetriever:
        def __init__(self, query=None, headers=None, query_domains=None, websocket=None, researcher=None):
            self.initialized = True
            # intentionally no search method

    results = await ResearchConductor._search(fake_self, NoSearchRetriever, "q")
    assert results == []

    # Should have logged an error about missing search method
    assert any("does not have a search method" in e for e in fake_logger.errors)

    # stream_output should not be called
    assert stream_capture.calls == []


@pytest.mark.asyncio
async def test_mcp_retriever_init_exception_round_021(monkeypatch):
    """
    If retriever __init__ raises, code should catch and (for MCP retriever + verbose) call mcp_error stream_output and return [].
    """
    stream_capture = AsyncStreamCapture()
    monkeypatch.setattr(researcher_mod, "stream_output", stream_capture)

    fake_researcher = types.SimpleNamespace(
        headers={},
        query_domains=[],
        websocket="wbs",
        verbose=True,
        cfg=types.SimpleNamespace(max_search_results_per_query=5),
    )
    fake_logger = FakeLogger()
    fake_self = types.SimpleNamespace(logger=fake_logger, researcher=fake_researcher)

    class BadMcPRetriever:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("boom init")

    results = await ResearchConductor._search(fake_self, BadMcPRetriever, "errq")
    assert results == []

    # stream_output should have been invoked once for the mcp_error branch
    assert len(stream_capture.calls) == 1
    category, etype, message_text, websocket = stream_capture.calls[0]
    assert category == "logs"
    assert etype == "mcp_error"
    assert "Error retrieving information from MCP server" in message_text or "Error retrieving information" in message_text

    # Logger should have recorded an error mentioning the retriever
    assert any("Error searching with" in e for e in fake_logger.errors)
