import asyncio
from typing import List, Dict

from gpt_researcher.retrievers.mcp.retriever import MCPRetriever


class DummyStreamer:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stage_starts: List[tuple] = []
        self.research_results: List[tuple] = []

    async def stream_error(self, msg: str):
        self.errors.append(msg)

    async def stream_warning(self, msg: str):
        self.warnings.append(msg)

    async def stream_stage_start(self, stage: str, desc: str):
        self.stage_starts.append((stage, desc))

    async def stream_research_results(self, n: int, total_length: int):
        self.research_results.append((n, total_length))


class DummyToolSelector:
    def __init__(self, selected):
        self._selected = selected

    async def select_relevant_tools(self, query, all_tools, max_tools=3):
        # return predetermined selection (could be empty)
        return self._selected


class DummyResearcher:
    def __init__(self, results):
        # results: list of dicts
        self._results = results

    async def conduct_research_with_tools(self, query, selected_tools):
        return list(self._results)


class DummyClientManager:
    def __init__(self, raise_on_close=False, called_flag: Dict = None):
        self.raise_on_close = raise_on_close
        self.called_flag = called_flag

    async def close_client(self):
        if self.called_flag is not None:
            self.called_flag["closed"] = True
        if self.raise_on_close:
            raise RuntimeError("close failed")


# Helpers to build an MCPRetriever without calling its real __init__
def make_retriever(
    *,
    query: str = "test",
    mcp_configs=None,
    all_tools=None,
    selected_tools=None,
    research_results=None,
    client_close_raises=False,
    client_called_flag=None,
):
    r = MCPRetriever.__new__(MCPRetriever)
    # minimal attributes used by search_async
    r.query = query
    r.mcp_configs = ([] if mcp_configs is None else mcp_configs)
    r.streamer = DummyStreamer()

    async def _get_all_tools():
        return [] if all_tools is None else list(all_tools)

    r._get_all_tools = _get_all_tools
    r.tool_selector = DummyToolSelector([] if selected_tools is None else selected_tools)
    r.mcp_researcher = DummyResearcher([] if research_results is None else research_results)
    r.client_manager = DummyClientManager(raise_on_close=client_close_raises, called_flag=client_called_flag)

    return r


def test_search_async_no_mcp_configs_round_014():
    """When mcp_configs is empty, search_async should return [] and stream an error."""
    retriever = make_retriever(mcp_configs=[])

    # run the async method deterministically
    results = asyncio.run(retriever.search_async(max_results=5))

    assert results == []
    # streamer should record the specific error message used in the code path
    assert retriever.streamer.errors, "Expected an error to be streamed when no configs are provided"
    assert "MCP retriever cannot proceed without server configurations." in retriever.streamer.errors[0]


def test_search_async_no_tools_round_014():
    """When _get_all_tools returns empty, search_async should warn and return []. Client cleanup must be invoked."""
    client_flag = {"closed": False}
    retriever = make_retriever(mcp_configs=["cfg"], all_tools=[], client_called_flag=client_flag)

    results = asyncio.run(retriever.search_async(max_results=3))

    assert results == []
    # stream_warning should have been called with the message about no MCP tools
    assert retriever.streamer.warnings, "Expected a warning when no MCP tools available"
    assert any("No MCP tools available" in w for w in retriever.streamer.warnings)
    # finally should attempt to close the client
    assert client_flag["closed"] is True


def test_search_async_no_selected_tools_round_014():
    """When tool_selector selects no tools, search_async should stream a warning and return []."""
    client_flag = {"closed": False}
    retriever = make_retriever(
        mcp_configs=["cfg"],
        all_tools=["tool1"],
        selected_tools=[],
        client_called_flag=client_flag,
    )

    results = asyncio.run(retriever.search_async(max_results=2))

    assert results == []
    assert retriever.streamer.warnings, "Expected a warning when no relevant tools are selected"
    assert any("No relevant tools selected" in w for w in retriever.streamer.warnings)
    assert client_flag["closed"] is True


def test_search_async_results_truncation_and_remaining_round_014():
    """Return more results than max_results to exercise truncation and the 'remaining results' branch. Also simulate client close raising an exception."""
    # Build 6 fake results with bodies of known lengths to validate total_content_length
    results = []
    # first result: long body (>400 chars) to trigger content_sample truncation
    long_body = "x" * 450
    results.append({"title": "Long", "href": "url1", "body": long_body})
    # next three: moderate bodies
    results.append({"title": "A", "href": "url2", "body": "hello"})
    results.append({"title": "B", "href": "url3", "body": "world"})
    results.append({"title": "C", "href": "url4", "body": "!"})
    # two more to count as remaining results
    results.append({"title": "D", "href": "url5", "body": "more"})
    results.append({"title": "E", "href": "url6", "body": "stuff"})

    client_flag = {"closed": False}
    retriever = make_retriever(
        mcp_configs=["cfg"],
        all_tools=["tool1"],
        selected_tools=["tool1"],
        research_results=results,
        client_close_raises=True,
        client_called_flag=client_flag,
    )

    # Ask for max_results=4 to force truncation from 6->4
    returned = asyncio.run(retriever.search_async(max_results=4))

    # Results should have been truncated to 4
    assert isinstance(returned, list)
    assert len(returned) == 4
    # The returned entries should equal the first four of the original results
    assert returned == results[:4]

    # stream_research_results must have been called with n == 4 and total length equal to sum of first 4 bodies
    assert retriever.streamer.research_results, "Expected stream_research_results to be called"
    n_reported, total_length_reported = retriever.streamer.research_results[-1]
    expected_total = sum(len(r["body"]) for r in results[:4])
    assert n_reported == 4
    assert total_length_reported == expected_total

    # client close should have been attempted even if it raised
    assert client_flag["closed"] is True
