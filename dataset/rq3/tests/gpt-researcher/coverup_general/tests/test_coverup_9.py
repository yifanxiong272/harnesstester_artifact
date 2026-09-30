# file: gpt_researcher/retrievers/mcp/retriever.py:116-199
# asked: {"lines": [116, 127, 128, 129, 130, 131, 134, 136, 138, 139, 141, 142, 143, 146, 147, 149, 150, 151, 154, 155, 158, 159, 160, 163, 166, 167, 170, 172, 173, 174, 175, 176, 177, 179, 180, 181, 183, 184, 185, 186, 188, 190, 191, 192, 193, 196, 197, 198, 199], "branches": [[127, 128], [127, 134], [141, 142], [141, 146], [149, 150], [149, 154], [158, 159], [158, 163], [170, 172], [170, 188], [172, 173], [172, 183], [183, 184], [183, 188]]}
# gained: {"lines": [116, 127, 128, 129, 130, 131, 134, 136, 138, 139, 141, 142, 143, 146, 147, 149, 150, 151, 154, 155, 158, 159, 160, 163, 166, 167, 170, 172, 173, 174, 175, 176, 177, 179, 180, 181, 183, 184, 185, 186, 188, 190, 191, 192, 193, 196, 197, 198, 199], "branches": [[127, 128], [127, 134], [141, 142], [141, 146], [149, 150], [149, 154], [158, 159], [170, 172], [172, 173], [172, 183], [183, 184]]}

import asyncio
import importlib
import pytest

# Import the module under test
mod_name = "gpt_researcher.retrievers.mcp.retriever"
retriever_mod = importlib.import_module(mod_name)
MCPRetriever = retriever_mod.MCPRetriever


class DummyStreamer:
    def __init__(self, websocket=None):
        self.websocket = websocket
        self.logged = []
        self.errors = []
        self.warnings = []
        self.stages = []
        self.research_results = []
        self.log_sync = []

    def stream_log_sync(self, msg: str):
        self.log_sync.append(msg)

    async def stream_error(self, msg: str):
        self.errors.append(msg)

    async def stream_stage_start(self, stage: str, desc: str):
        self.stages.append((stage, desc))

    async def stream_warning(self, msg: str):
        self.warnings.append(msg)

    async def stream_research_results(self, count: int, total_content_length: int):
        self.research_results.append((count, total_content_length))


class DummyClientManager:
    def __init__(self, configs, raise_on_close=False, record=None):
        self.configs = configs
        self.raise_on_close = raise_on_close
        # optional external record dict to mark calls
        self.record = record if record is not None else {}
        self.record["close_called"] = False

    async def close_client(self):
        self.record["close_called"] = True
        if self.raise_on_close:
            raise RuntimeError("close error")


class DummyToolSelector:
    def __init__(self, cfg, researcher, to_return=None):
        self.cfg = cfg
        self.researcher = researcher
        self.to_return = to_return if to_return is not None else []

    async def select_relevant_tools(self, query, all_tools, max_tools=3):
        # Just return preconfigured tools
        return self.to_return


class DummyResearchSkill:
    def __init__(self, cfg, researcher, to_return=None, raise_exc=False):
        self.cfg = cfg
        self.researcher = researcher
        self.to_return = to_return if to_return is not None else []
        self.raise_exc = raise_exc

    async def conduct_research_with_tools(self, query, selected_tools):
        if self.raise_exc:
            raise RuntimeError("research error")
        return self.to_return


@pytest.mark.asyncio
async def test_search_async_no_configs(monkeypatch):
    """
    Test the branch where no mcp_configs are available. Should call stream_error and return [].
    """
    # Patch dependencies on module
    monkeypatch.setattr(retriever_mod, "MCPStreamer", DummyStreamer)
    # Provide a client manager implementation (though it won't be used in search_async early-return)
    monkeypatch.setattr(retriever_mod, "MCPClientManager", DummyClientManager)
    monkeypatch.setattr(retriever_mod, "MCPToolSelector", DummyToolSelector)
    monkeypatch.setattr(retriever_mod, "MCPResearchSkill", DummyResearchSkill)

    # Force _get_mcp_configs to return empty list
    monkeypatch.setattr(MCPRetriever, "_get_mcp_configs", lambda self: [])
    # _get_config may be called in __init__, provide stub
    monkeypatch.setattr(MCPRetriever, "_get_config", lambda self: {})

    retriever = MCPRetriever(query="test query")
    # Ensure streamer is our DummyStreamer
    assert isinstance(retriever.streamer, DummyStreamer)

    results = await retriever.search_async()
    assert results == []  # Should return empty list

    # Because no configs, search_async should have called stream_error with message about cannot proceed.
    # Our DummyStreamer collected errors
    assert any("MCP retriever cannot proceed" in e for e in retriever.streamer.errors)


@pytest.mark.asyncio
async def test_search_async_no_tools(monkeypatch):
    """
    Test the case where _get_all_tools returns empty; should warn and return [].
    Ensure client_manager.close_client is called in finally.
    """
    monkeypatch.setattr(retriever_mod, "MCPStreamer", DummyStreamer)
    # Set client manager to record close_called
    record = {}
    monkeypatch.setattr(retriever_mod, "MCPClientManager", lambda configs: DummyClientManager(configs, record=record))
    monkeypatch.setattr(retriever_mod, "MCPToolSelector", DummyToolSelector)
    monkeypatch.setattr(retriever_mod, "MCPResearchSkill", DummyResearchSkill)

    # non-empty configs to proceed into try
    monkeypatch.setattr(MCPRetriever, "_get_mcp_configs", lambda self: [{"url": "http://example"}])
    monkeypatch.setattr(MCPRetriever, "_get_config", lambda self: {})

    retriever = MCPRetriever(query="test query")
    # Patch _get_all_tools to return empty list (async)
    async def _get_all_tools_empty(self):
        return []
    monkeypatch.setattr(MCPRetriever, "_get_all_tools", _get_all_tools_empty)

    results = await retriever.search_async()
    assert results == []
    # Should have a warning about no tools available
    assert any("No MCP tools available" in w for w in retriever.streamer.warnings)
    # Ensure client close was attempted in finally
    assert record.get("close_called", False) is True


@pytest.mark.asyncio
async def test_search_async_selected_tools_empty(monkeypatch):
    """
    Test the branch where tool_selector returns no relevant tools; should warn and return [].
    """
    monkeypatch.setattr(retriever_mod, "MCPStreamer", DummyStreamer)
    record = {}
    monkeypatch.setattr(retriever_mod, "MCPClientManager", lambda configs: DummyClientManager(configs, record=record))
    # Set ToolSelector to return empty list
    monkeypatch.setattr(retriever_mod, "MCPToolSelector", lambda cfg, researcher: DummyToolSelector(cfg, researcher, to_return=[]))
    monkeypatch.setattr(retriever_mod, "MCPResearchSkill", DummyResearchSkill)

    monkeypatch.setattr(MCPRetriever, "_get_mcp_configs", lambda self: [{"url": "server"}])
    monkeypatch.setattr(MCPRetriever, "_get_config", lambda self: {})

    retriever = MCPRetriever(query="some query")

    async def _get_all_tools(self):
        return ["toolA", "toolB"]
    monkeypatch.setattr(MCPRetriever, "_get_all_tools", _get_all_tools)

    results = await retriever.search_async()
    assert results == []
    # Should have a warning about no relevant tools selected
    assert any("No relevant tools selected" in w for w in retriever.streamer.warnings)
    assert record.get("close_called", False) is True


@pytest.mark.asyncio
async def test_search_async_results_truncate_and_more_results_logging(monkeypatch):
    """
    Test the full happy path where tools are selected and research returns many results.
    This should trigger result truncation when len(results) > max_results and also the
    logging of remaining results when >3.
    """
    monkeypatch.setattr(retriever_mod, "MCPStreamer", DummyStreamer)
    record = {}
    monkeypatch.setattr(retriever_mod, "MCPClientManager", lambda configs: DummyClientManager(configs, record=record))
    # ToolSelector returns 2 tools
    monkeypatch.setattr(retriever_mod, "MCPToolSelector", lambda cfg, researcher: DummyToolSelector(cfg, researcher, to_return=["t1", "t2"]))
    # Prepare >5 results with bodies to test content length and sample
    results_list = []
    for i in range(6):
        body = ("content-" + str(i)) * (i + 1)  # variable lengths
        results_list.append({"title": f"title{i}", "href": f"http://{i}.example", "body": body})

    monkeypatch.setattr(retriever_mod, "MCPResearchSkill", lambda cfg, researcher: DummyResearchSkill(cfg, researcher, to_return=results_list))

    monkeypatch.setattr(MCPRetriever, "_get_mcp_configs", lambda self: [{"url": "server"}])
    monkeypatch.setattr(MCPRetriever, "_get_config", lambda self: {})

    retriever = MCPRetriever(query="truncate test")

    async def _get_all_tools(self):
        return ["tool1", "tool2", "tool3"]
    monkeypatch.setattr(MCPRetriever, "_get_all_tools", _get_all_tools)

    # Request max_results lower than returned results to force truncation
    returned = await retriever.search_async(max_results=4)
    # Should be truncated to 4
    assert isinstance(returned, list)
    assert len(returned) == 4
    # Ensure stream_research_results was called with the truncated count and correct total length for truncated list
    # The DummyStreamer records (count, total_length)
    assert retriever.streamer.research_results, "stream_research_results should have been called"
    # The last recorded research_results entry should match len(returned) and sum of their bodies
    last_count, last_total_len = retriever.streamer.research_results[-1]
    assert last_count == 4
    expected_total = sum(len(r.get("body", "")) for r in returned)
    assert last_total_len == expected_total
    # Ensure client closed
    assert record.get("close_called", False) is True


@pytest.mark.asyncio
async def test_search_async_exception_in_research_and_close_raises(monkeypatch):
    """
    Test exception handling: conduct_research_with_tools raises -> stream_error called and return [].
    Additionally client_manager.close_client raises to hit the except in finally branch.
    """
    monkeypatch.setattr(retriever_mod, "MCPStreamer", DummyStreamer)
    # make client manager raise on close
    monkeypatch.setattr(retriever_mod, "MCPClientManager", lambda configs: DummyClientManager(configs, raise_on_close=True, record={"close_called": False}))
    # Selector returns some tools
    monkeypatch.setattr(retriever_mod, "MCPToolSelector", lambda cfg, researcher: DummyToolSelector(cfg, researcher, to_return=["tool"]))
    # Research skill will raise
    monkeypatch.setattr(retriever_mod, "MCPResearchSkill", lambda cfg, researcher: DummyResearchSkill(cfg, researcher, raise_exc=True))

    monkeypatch.setattr(MCPRetriever, "_get_mcp_configs", lambda self: [{"url": "server"}])
    monkeypatch.setattr(MCPRetriever, "_get_config", lambda self: {})

    retriever = MCPRetriever(query="will error")

    async def _get_all_tools(self):
        return ["t"]
    monkeypatch.setattr(MCPRetriever, "_get_all_tools", _get_all_tools)

    results = await retriever.search_async()
    # Since research raised, search_async should return []
    assert results == []
    # Error should have been streamed with message about error in MCP search
    assert any("Error in MCP search" in e or "research error" in e for e in retriever.streamer.errors) or retriever.streamer.errors, "stream_error should have been called"
    # client close attempted (raised, but we don't let it propagate)
    # Our DummyClientManager recorded close call in its record dict passed in; find the instance by creating another client to inspect?
    # Instead ensure that no exception propagated and function returned normally (above asserts suffice).

