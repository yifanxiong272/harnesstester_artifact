import pytest
import types
from typing import Any, List, Tuple

# Import the module under test
from gpt_researcher.skills import researcher as researcher_mod

class DummyLogger:
    def __init__(self):
        self.infos: List[str] = []
        self.errors: List[str] = []

    def info(self, msg: str) -> None:
        self.infos.append(msg)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

class DummyResearcher:
    def __init__(self, verbose: bool, websocket: Any = None):
        self.verbose = verbose
        self.websocket = websocket

class FakeSelf:
    def __init__(self, researcher_verbose: bool, websocket: Any = None):
        self.logger = DummyLogger()
        self.researcher = DummyResearcher(researcher_verbose, websocket)
        # placeholder for an async _execute_mcp_research; tests will assign the coroutine
        self._execute_mcp_research = None


@pytest.mark.asyncio
async def test_execute_mcp_research_for_queries_success_round_033(monkeypatch):
    """
    - _execute_mcp_research returns a single MCP result with a non-empty body.
    - researcher.verbose is True, so stream_output should be invoked for cached results.
    - The function should return a list with one context entry containing the expected fields.
    """
    calls: List[Tuple] = []

    async def fake_stream_output(channel, event, message, websocket):
        # record the call arguments so tests can assert on them deterministically
        calls.append((channel, event, message, websocket))

    monkeypatch.setattr(researcher_mod, "stream_output", fake_stream_output)

    fake = FakeSelf(researcher_verbose=True, websocket="ws-object")

    async def fake_execute_mcp_research(retriever, query):
        # deterministic single result with body/title/href
        return [{"body": "the content", "href": "http://example", "title": "Example"}]

    # attach the coroutine to the fake self
    fake._execute_mcp_research = types.MethodType(lambda self, r, q: fake_execute_mcp_research(r, q), fake)

    result = await researcher_mod.ResearchConductor._execute_mcp_research_for_queries(fake, ["query1"], ["retriever1"])  # type: ignore

    # oracle: returned one context entry with expected keys and values
    assert isinstance(result, list)
    assert len(result) == 1
    entry = result[0]
    assert entry["content"] == "the content"
    assert entry["url"] == "http://example"
    assert entry["title"] == "Example"
    assert entry["query"] == "query1"
    assert entry["source_type"] == "mcp"

    # stream_output should have been called once for cached results (verbose True)
    assert len(calls) == 1
    channel, event, message, websocket = calls[0]
    assert channel == "logs"
    assert event == "mcp_results_cached"
    # message should mention Cached and the number of results deterministically
    assert "Cached 1 MCP results" in message
    assert websocket == "ws-object"


@pytest.mark.asyncio
async def test_execute_mcp_research_for_queries_empty_results_no_stream_round_033(monkeypatch):
    """
    - _execute_mcp_research returns an empty list (falsy) and researcher.verbose is False.
    - No stream_output should be called and the returned list should be empty.
    """
    calls: List[Tuple] = []

    async def fake_stream_output(channel, event, message, websocket):
        calls.append((channel, event, message, websocket))

    monkeypatch.setattr(researcher_mod, "stream_output", fake_stream_output)

    fake = FakeSelf(researcher_verbose=False, websocket=None)

    async def fake_execute_mcp_research_empty(retriever, query):
        return []

    fake._execute_mcp_research = types.MethodType(lambda self, r, q: fake_execute_mcp_research_empty(r, q), fake)

    result = await researcher_mod.ResearchConductor._execute_mcp_research_for_queries(fake, ["q"], ["r"])  # type: ignore

    # oracle: no context entries added
    assert result == []

    # No stream_output calls when verbose is False
    assert calls == []


@pytest.mark.asyncio
async def test_execute_mcp_research_for_queries_exception_streams_error_round_033(monkeypatch):
    """
    - _execute_mcp_research raises an exception. The method should catch it, log an error,
      and, when verbose is True, call stream_output with mcp_cache_error.
    - The returned list should be empty and logger should have recorded the error.
    """
    calls: List[Tuple] = []

    async def fake_stream_output(channel, event, message, websocket):
        calls.append((channel, event, message, websocket))

    monkeypatch.setattr(researcher_mod, "stream_output", fake_stream_output)

    fake = FakeSelf(researcher_verbose=True, websocket="ws-exc")

    async def fake_execute_mcp_research_raise(retriever, query):
        raise RuntimeError("boom")

    fake._execute_mcp_research = types.MethodType(lambda self, r, q: fake_execute_mcp_research_raise(r, q), fake)

    result = await researcher_mod.ResearchConductor._execute_mcp_research_for_queries(fake, ["the-query"], ["retriever-x"])  # type: ignore

    # oracle: result still returns an empty list (errors are caught and processing continues)
    assert result == []

    # the logger.error should have recorded an error message containing the query and exception text
    assert any("the-query" in msg and "boom" in msg for msg in fake.logger.errors)

    # Because verbose is True, stream_output should have been called for the cache error branch
    assert len(calls) == 1
    channel, event, message, websocket = calls[0]
    assert channel == "logs"
    assert event == "mcp_cache_error"
    assert "MCP research error" in message
    assert websocket == "ws-exc"
