import asyncio
import pytest

from gpt_researcher.retrievers.mcp.retriever import MCPRetriever

# Lightweight async stubs to record calls deterministically
class StreamerStub:
    def __init__(self):
        self.calls = []

    async def stream_error(self, msg):
        self.calls.append(("error", msg))

    async def stream_warning(self, msg):
        self.calls.append(("warning", msg))

    async def stream_stage_start(self, stage, desc):
        self.calls.append(("stage_start", stage, desc))

    async def stream_research_results(self, count, total_content_length):
        self.calls.append(("research_results", count, total_content_length))


class ToolSelectorStub:
    def __init__(self, selected_tools):
        self.selected_tools = selected_tools
        self.calls = []

    async def select_relevant_tools(self, query, all_tools, max_tools=3):
        # record inputs to support assertions
        self.calls.append((query, list(all_tools), max_tools))
        return self.selected_tools


class ResearcherStub:
    def __init__(self, results):
        self.results = results
        self.calls = []

    async def conduct_research_with_tools(self, query, selected_tools):
        self.calls.append((query, list(selected_tools)))
        return self.results


class ClientManagerStub:
    def __init__(self, raise_on_close=False):
        self.closed = False
        self.raise_on_close = raise_on_close

    async def close_client(self):
        self.closed = True
        if self.raise_on_close:
            raise RuntimeError("close failed")


# Helper to build an MCPRetriever-like instance without invoking its real __init__
def make_retriever(
    *,
    mcp_configs=None,
    all_tools=None,
    selected_tools=None,
    research_results=None,
    get_all_tools_exception=False,
    client_close_raises=False,
    query="test-query",
):
    r = object.__new__(MCPRetriever)
    # Basic attributes used by search_async
    r.query = query
    r.mcp_configs = mcp_configs
    r.streamer = StreamerStub()

    async def _get_all_tools():
        if get_all_tools_exception:
            raise RuntimeError("get tools fail")
        return list(all_tools) if all_tools is not None else []

    r._get_all_tools = _get_all_tools
    r.tool_selector = ToolSelectorStub(selected_tools if selected_tools is not None else [])
    r.mcp_researcher = ResearcherStub(research_results if research_results is not None else [])
    r.client_manager = ClientManagerStub(raise_on_close=client_close_raises)
    return r


@pytest.mark.asyncio
async def test_no_mcp_configs_round_014():
    """When mcp_configs is empty, search_async should stream an error and return []"""
    retriever = make_retriever(mcp_configs=[], all_tools=["toolA"], selected_tools=["toolA"])

    result = await retriever.search_async(max_results=5)

    assert result == []  # empty due to missing mcp_configs
    # streamer should have received an error message
    assert any(call[0] == "error" and "MCP retriever cannot proceed" in call[1] for call in retriever.streamer.calls)
    # Important: When mcp_configs is missing the function returns before the try/finally cleanup,
    # so client_manager.close_client is NOT called. Expect closed == False.
    assert retriever.client_manager.closed is False


@pytest.mark.asyncio
async def test_no_tools_round_014():
    """When _get_all_tools returns empty list, search_async should stream a warning and return []"""
    retriever = make_retriever(mcp_configs=[{"host": "x"}], all_tools=[], selected_tools=["toolA"])

    result = await retriever.search_async(max_results=5)

    assert result == []
    # Should have called stage start for Stage 1 and then a warning about no tools
    assert any(call[0] == "stage_start" and call[1] == "Stage 1" for call in retriever.streamer.calls)
    assert any(call[0] == "warning" and "No MCP tools available" in call[1] for call in retriever.streamer.calls)
    assert retriever.client_manager.closed is True


@pytest.mark.asyncio
async def test_no_selected_tools_round_014():
    """When no relevant tools are selected, search_async should stream a warning and return []"""
    retriever = make_retriever(mcp_configs=[{"host": "x"}], all_tools=["toolA"], selected_tools=[])

    result = await retriever.search_async(max_results=5)

    assert result == []
    # Should have called Stage 2 start and then a warning about no relevant tools
    assert any(call[0] == "stage_start" and call[1] == "Stage 2" for call in retriever.streamer.calls)
    assert any(call[0] == "warning" and "No relevant tools selected" in call[1] for call in retriever.streamer.calls)
    assert retriever.client_manager.closed is True


@pytest.mark.asyncio
async def test_results_trimming_round_014():
    """When results exceed max_results, they are trimmed and research results are streamed"""
    # create 5 results with bodies to exercise content length and first-3 logging
    results = [
        {"title": f"Title {i}", "href": f"http://example/{i}", "body": "x" * (10 + i)}
        for i in range(5)
    ]
    retriever = make_retriever(
        mcp_configs=[{"host": "x"}],
        all_tools=["t1"],
        selected_tools=["t1"],
        research_results=results,
    )

    # request only 2 results so trimming branch is exercised
    out = await retriever.search_async(max_results=2)

    assert isinstance(out, list)
    assert len(out) == 2  # trimmed to max_results
    # streamer should have received the research results summary with correct count and total content length
    assert any(call[0] == "research_results" and call[1] == 2 for call in retriever.streamer.calls)
    assert retriever.client_manager.closed is True


@pytest.mark.asyncio
async def test_results_more_than_three_and_close_exception_round_014():
    """When more than three results are returned, the code logs remaining results.
    Also, ensure client_manager.close_client exceptions are handled gracefully.
    """
    # 5 results so >3 branch is exercised. Use max_results large so trimming does not occur.
    results = [
        {"title": f"Title {i}", "href": f"http://example/{i}", "body": "y" * (100 + i)}
        for i in range(5)
    ]
    retriever = make_retriever(
        mcp_configs=[{"host": "x"}],
        all_tools=["t1"],
        selected_tools=["t1"],
        research_results=results,
        client_close_raises=True,  # force close_client to raise to hit cleanup-except branch
    )

    out = await retriever.search_async(max_results=10)

    # Should return all results (no trimming)
    assert isinstance(out, list)
    assert len(out) == 5
    # Ensure that streamer research_results was called with full count
    assert any(call[0] == "research_results" and call[1] == 5 for call in retriever.streamer.calls)
    # close_client should have been attempted and recorded as closed even if it raised
    assert retriever.client_manager.closed is True


@pytest.mark.asyncio
async def test_exception_in_stage_round_014():
    """If _get_all_tools raises, search_async should stream an error and return [] (except block)"""
    retriever = make_retriever(
        mcp_configs=[{"host": "x"}],
        get_all_tools_exception=True,
    )

    out = await retriever.search_async(max_results=3)

    assert out == []
    # Should have an error streamed mentioning MCP search error
    assert any(call[0] == "error" for call in retriever.streamer.calls)
    # cleanup should have been attempted
    assert retriever.client_manager.closed is True
