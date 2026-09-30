# file: gpt_researcher/skills/researcher.py:393-447
# asked: {"lines": [404, 406, 407, 409, 410, 411, 412, 413, 414, 415, 416, 418, 419, 420, 421, 422, 423, 424, 426, 428, 430, 431, 432, 433, 434, 435, 437, 438, 439, 440, 441, 442, 443, 444, 447], "branches": [[406, 407], [406, 447], [409, 406], [409, 410], [412, 409], [412, 413], [413, 414], [413, 428], [418, 413], [418, 419], [430, 409], [430, 431], [439, 409], [439, 440]]}
# gained: {"lines": [404, 406, 407, 409, 410, 411, 412, 413, 414, 415, 416, 418, 419, 420, 421, 422, 423, 424, 426, 428, 430, 431, 432, 433, 434, 435, 437, 438, 439, 440, 441, 442, 443, 444, 447], "branches": [[406, 407], [406, 447], [409, 406], [409, 410], [412, 413], [413, 414], [413, 428], [418, 413], [418, 419], [430, 409], [430, 431], [439, 440]]}

import pytest
import asyncio

@pytest.mark.asyncio
async def test_execute_mcp_research_for_queries_basic(monkeypatch):
    # Import inside test to ensure monkeypatch can patch module attributes
    from gpt_researcher.skills.researcher import ResearchConductor
    # Prepare a recorder for stream_output calls
    stream_calls = []

    async def fake_stream_output(stream_name, event_key, message, websocket):
        stream_calls.append((stream_name, event_key, message, websocket))

    # Patch the stream_output used in the researcher module
    monkeypatch.setattr("gpt_researcher.skills.researcher.stream_output", fake_stream_output)

    # Create instance without calling its __init__
    rc = ResearchConductor.__new__(ResearchConductor)

    # Dummy logger that records info/error calls
    info_calls = []
    error_calls = []

    class DummyLogger:
        def info(self, msg):
            info_calls.append(msg)
        def error(self, msg):
            error_calls.append(msg)

    rc.logger = DummyLogger()

    # researcher attribute with verbose False (so stream_output should not be called)
    class DummyResearcher:
        verbose = False
        websocket = "ws1"

    rc.researcher = DummyResearcher()

    # Provide _execute_mcp_research to return one valid result
    async def fake_execute(retriever, query):
        await asyncio.sleep(0)  # allow proper async context switch
        return [{"body": "contentX", "href": "http://x", "title": "TitleX"}]

    rc._execute_mcp_research = fake_execute

    # Call the target method
    queries = ["query1"]
    retrievers = ["retr1"]
    result = await rc._execute_mcp_research_for_queries(queries, retrievers)

    # Assertions: one context entry returned with expected fields
    assert isinstance(result, list)
    assert len(result) == 1
    entry = result[0]
    assert entry["content"] == "contentX"
    assert entry["url"] == "http://x"
    assert entry["title"] == "TitleX"
    assert entry["query"] == "query1"
    assert entry["source_type"] == "mcp"

    # stream_output should not have been called because verbose=False
    assert stream_calls == []

    # Logger info should have been called at least twice (starting message and added message)
    assert any("Executing MCP research for query" in m for m in info_calls)
    assert any("Added 1 MCP results for query" in m for m in info_calls)


@pytest.mark.asyncio
async def test_execute_mcp_research_for_queries_with_empty_content_and_exception(monkeypatch):
    from gpt_researcher.skills.researcher import ResearchConductor
    # Recorder for stream_output calls
    stream_calls = []

    async def fake_stream_output(stream_name, event_key, message, websocket):
        stream_calls.append((stream_name, event_key, message, websocket))

    monkeypatch.setattr("gpt_researcher.skills.researcher.stream_output", fake_stream_output)

    rc = ResearchConductor.__new__(ResearchConductor)

    # Logger to capture messages
    info_calls = []
    error_calls = []

    class DummyLogger:
        def info(self, msg):
            info_calls.append(msg)
        def error(self, msg):
            error_calls.append(msg)

    rc.logger = DummyLogger()

    # researcher verbose True to trigger stream_output in both success and exception paths
    class DummyResearcher:
        verbose = True
        websocket = "ws2"

    rc.researcher = DummyResearcher()

    # _execute_mcp_research returns different behaviors depending on retriever
    async def fake_execute(retriever, query):
        await asyncio.sleep(0)
        if retriever == "r1":
            # Two results: one with empty body (should be skipped), one with content
            return [
                {"body": "", "href": "http://empty", "title": "Empty"},
                {"body": "useful content", "href": "http://useful", "title": "Useful"},
            ]
        elif retriever == "r2":
            # Simulate an error to exercise exception handling path
            raise RuntimeError("simulated failure")
        else:
            return []

    rc._execute_mcp_research = fake_execute

    queries = ["Q"]
    retrievers = ["r1", "r2"]
    result = await rc._execute_mcp_research_for_queries(queries, retrievers)

    # Only the non-empty content entry should be returned
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["content"] == "useful content"
    assert result[0]["url"] == "http://useful"
    assert result[0]["title"] == "Useful"
    assert result[0]["query"] == "Q"
    assert result[0]["source_type"] == "mcp"

    # stream_output should have been called twice:
    # 1) for cached results from r1 (len 2 results reported)
    # 2) for mcp_cache_error when r2 raised
    assert len(stream_calls) == 2
    first = stream_calls[0]
    second = stream_calls[1]

    assert first[1] == "mcp_results_cached"
    assert "✅ Cached 2 MCP results from query 1/1" in first[2]
    assert first[3] == "ws2"

    assert second[1] == "mcp_cache_error"
    assert "⚠️ MCP research error for query 1" in second[2]
    assert second[3] == "ws2"

    # Logger should have recorded an error message for the exception
    assert any("Error in MCP research for query" in m for m in error_calls)
