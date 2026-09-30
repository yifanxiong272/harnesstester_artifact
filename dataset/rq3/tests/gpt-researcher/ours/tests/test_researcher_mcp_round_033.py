import asyncio
from types import SimpleNamespace
import importlib
import pytest

mod = importlib.import_module("gpt_researcher.skills.researcher")
ResearchConductor = mod.ResearchConductor

@pytest.mark.asyncio
async def test_execute_mcp_research_for_queries_success_round_033():
    """
    - _execute_mcp_research returns two results (one with body, one without)
    - researcher.verbose True -> stream_output should be awaited for cached results
    - final returned context should include only the result that has a body
    """
    # Arrange
    researcher = SimpleNamespace(verbose=True, websocket="ws://fake")
    conductor = ResearchConductor(researcher)

    logs = []
    conductor.logger = SimpleNamespace(
        info=lambda *a, **k: logs.append(("info", a)),
        error=lambda *a, **k: logs.append(("error", a)),
    )

    async def fake_execute(self, retriever, query):
        # two results: first has body, second empty body
        return [
            {"body": "content1", "href": "http://a", "title": "t1"},
            {"body": "", "href": "http://b", "title": "t2"},
        ]

    stream_calls = []

    async def fake_stream_output(channel, tag, message, websocket):
        # capture calls for assertion
        stream_calls.append((channel, tag, message, websocket))

    # Patch module-level symbols and restore after test
    original_exec = mod.ResearchConductor._execute_mcp_research
    original_stream = mod.stream_output
    try:
        mod.ResearchConductor._execute_mcp_research = fake_execute
        mod.stream_output = fake_stream_output

        # Act
        result = await conductor._execute_mcp_research_for_queries(["q1"], ["r1"])

        # Assert
        # Only the result with non-empty body should be converted into context_entry
        assert result == [
            {
                "content": "content1",
                "url": "http://a",
                "title": "t1",
                "query": "q1",
                "source_type": "mcp",
            }
        ]

        # stream_output should be called once for cached results because verbose=True
        assert len(stream_calls) == 1
        channel, tag, message, websocket = stream_calls[0]
        assert channel == "logs"
        assert tag == "mcp_results_cached"
        # message should mention the count and query index/total
        assert "Cached 2 MCP results from query 1/1" in message
        assert websocket == researcher.websocket

    finally:
        mod.ResearchConductor._execute_mcp_research = original_exec
        mod.stream_output = original_stream


@pytest.mark.asyncio
async def test_execute_mcp_research_for_queries_exception_round_033():
    """
    - _execute_mcp_research raises an exception
    - researcher.verbose True -> stream_output should be awaited for cache error
    - function should continue and return an empty list when all retrievers fail
    """
    researcher = SimpleNamespace(verbose=True, websocket="ws://fake-ws")
    conductor = ResearchConductor(researcher)

    logs = []
    conductor.logger = SimpleNamespace(
        info=lambda *a, **k: logs.append(("info", a)),
        error=lambda *a, **k: logs.append(("error", a)),
    )

    async def raising_execute(self, retriever, query):
        raise RuntimeError("boom")

    stream_calls = []

    async def fake_stream_output(channel, tag, message, websocket):
        stream_calls.append((channel, tag, message, websocket))

    original_exec = mod.ResearchConductor._execute_mcp_research
    original_stream = mod.stream_output
    try:
        mod.ResearchConductor._execute_mcp_research = raising_execute
        mod.stream_output = fake_stream_output

        result = await conductor._execute_mcp_research_for_queries(["qX"], ["rX"])

        # Should gracefully return empty list when retriever raises
        assert result == []

        # logger.error should have been invoked at least once
        assert any(entry[0] == "error" for entry in logs)

        # Because verbose=True, stream_output should be invoked for the cache error
        assert len(stream_calls) == 1
        channel, tag, message, websocket = stream_calls[0]
        assert channel == "logs"
        assert tag == "mcp_cache_error"
        # message should mention the MCP research error for query index 1
        assert "MCP research error for query 1" in message or "MCP research error for query 1," in message
        assert websocket == researcher.websocket

    finally:
        mod.ResearchConductor._execute_mcp_research = original_exec
        mod.stream_output = original_stream
