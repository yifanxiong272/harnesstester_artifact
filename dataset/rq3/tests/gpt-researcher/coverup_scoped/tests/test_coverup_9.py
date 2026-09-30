# file: gpt_researcher/retrievers/mcp/retriever.py:201-298
# asked: {"lines": [201, 215, 216, 217, 218, 219, 222, 224, 226, 228, 231, 232, 235, 236, 237, 238, 239, 240, 243, 245, 246, 247, 250, 251, 252, 253, 254, 255, 258, 259, 260, 261, 262, 263, 265, 267, 268, 271, 272, 275, 278, 279, 280, 281, 284, 285, 286, 288, 290, 292, 294, 295, 296, 298], "branches": [[215, 216], [215, 222], [246, 247], [246, 250], [250, 251], [250, 265], [278, 0], [278, 279]]}
# gained: {"lines": [201, 215, 216, 217, 218, 219, 222, 224, 226, 228, 231, 232, 235, 236, 237, 238, 239, 240, 243, 245, 246, 250, 265, 267, 268, 271, 272, 275, 278, 279, 284, 285, 286, 288, 290, 292, 294, 295, 296, 298], "branches": [[215, 216], [215, 222], [246, 250], [250, 265], [278, 279]]}

import asyncio
import importlib
import pytest

MODULE_PATH = "gpt_researcher.retrievers.mcp.retriever"


class DummyClientManager:
    def __init__(self, configs):
        self.configs = configs


class DummyToolSelector:
    def __init__(self, cfg, researcher):
        self.cfg = cfg
        self.researcher = researcher


class DummyResearchSkill:
    def __init__(self, cfg, researcher):
        self.cfg = cfg
        self.researcher = researcher


class FakeStreamer:
    def __init__(self, websocket):
        self.websocket = websocket
        self.logged = []

    def stream_log_sync(self, msg: str):
        # Keep messages for inspection
        self.logged.append(msg)


def setup_minimal_module(monkeypatch, module, mcp_configs_value):
    """
    Replace heavy MCP dependencies in the module with lightweight dummies
    and ensure _get_mcp_configs returns the provided value.
    """
    # Replace resource-heavy classes with dummies
    monkeypatch.setattr(module, "MCPClientManager", DummyClientManager)
    monkeypatch.setattr(module, "MCPToolSelector", DummyToolSelector)
    monkeypatch.setattr(module, "MCPResearchSkill", DummyResearchSkill)
    monkeypatch.setattr(module, "MCPStreamer", FakeStreamer)

    # Force _get_mcp_configs to return desired value
    monkeypatch.setattr(module.MCPRetriever, "_get_mcp_configs", lambda self: mcp_configs_value)

    # Keep _get_config simple as it's called in __init__
    monkeypatch.setattr(module.MCPRetriever, "_get_config", lambda self: {"llm": "dummy"})


def test_search_no_configs_returns_empty_and_logs(monkeypatch):
    """
    When no MCP configs are available, search should return [] and call streamer.stream_log_sync
    with the expected message.
    """
    module = importlib.import_module(MODULE_PATH)
    setup_minimal_module(monkeypatch, module, mcp_configs_value=[])

    # Instantiate retriever; __init__ will use the mocked _get_mcp_configs which returns []
    retriever = module.MCPRetriever("some query", researcher=None)

    # Ensure we have the fake streamer
    assert isinstance(retriever.streamer, FakeStreamer)

    results = retriever.search(max_results=5)

    # Should return empty list
    assert results == []

    # The streamer should have received at least one message about inability to proceed
    assert any("MCP retriever cannot proceed" in msg or "No MCP server configurations" in msg for msg in retriever.streamer.logged)


@pytest.mark.asyncio
async def test_search_with_running_event_loop_uses_thread_and_returns_results(monkeypatch):
    """
    When called from within a running event loop, search should detect that and
    run the async search in a separate thread's event loop, returning the coroutine result.
    """
    module = importlib.import_module(MODULE_PATH)
    setup_minimal_module(monkeypatch, module, mcp_configs_value=[{"url": "http://x"}])

    # Define an async search_async that will be executed in the new thread's event loop
    async def fake_search_async(self, max_results=10):
        await asyncio.sleep(0)  # yield control briefly
        return [{"id": "threaded", "max": max_results}]

    # Patch the class method so instances use this coroutine
    monkeypatch.setattr(module.MCPRetriever, "search_async", fake_search_async, raising=True)

    retriever = module.MCPRetriever("async query", researcher=None)

    # Call the synchronous search method from inside running event loop
    results = retriever.search(max_results=2)

    assert isinstance(results, list)
    assert results == [{"id": "threaded", "max": 2}]
    # Ensure initial streamer logs were produced on initialization
    assert any("Initializing MCP retriever" in msg or "Found 1 MCP server configurations" in msg for msg in retriever.streamer.logged)


def test_search_without_running_loop_uses_asyncio_run(monkeypatch):
    """
    When no event loop is running (normal synchronous context), search should call asyncio.run on the coroutine.
    """
    module = importlib.import_module(MODULE_PATH)
    setup_minimal_module(monkeypatch, module, mcp_configs_value=[{"url": "http://y"}])

    async def fake_search_async(self, max_results=10):
        return [{"id": "sync", "max": max_results}]

    monkeypatch.setattr(module.MCPRetriever, "search_async", fake_search_async, raising=True)

    retriever = module.MCPRetriever("sync query", researcher=None)

    # Determine whether an event loop is running in a safe way
    try:
        running = asyncio.get_running_loop().is_running()
    except RuntimeError:
        running = False

    assert not running

    results = retriever.search(max_results=3)
    assert results == [{"id": "sync", "max": 3}]
    assert any("Initializing MCP retriever" in msg or "Found 1 MCP server configurations" in msg for msg in retriever.streamer.logged)


def test_search_outer_exception_caught_and_logged(monkeypatch):
    """
    Force an unexpected exception (not RuntimeError) from asyncio.get_running_loop to hit the outer exception handler.
    The search should catch the exception, log it via streamer.stream_log_sync and return [].
    """
    module = importlib.import_module(MODULE_PATH)
    setup_minimal_module(monkeypatch, module, mcp_configs_value=[{"url": "http://z"}])

    # Make get_running_loop raise a ValueError to trigger outer except (not the inner RuntimeError handler)
    def raise_value_error():
        raise ValueError("forced failure")

    # Patch the asyncio.get_running_loop used by the module to raise
    monkeypatch.setattr(module, "asyncio", module.asyncio)  # ensure module.asyncio is present
    monkeypatch.setattr(module.asyncio, "get_running_loop", raise_value_error)

    # Use a search_async that would return something if called, but it should not be reached
    async def fake_search_async(self, max_results=10):
        return [{"id": "should_not_be_called"}]

    monkeypatch.setattr(module.MCPRetriever, "search_async", fake_search_async, raising=True)

    retriever = module.MCPRetriever("error query", researcher=None)

    results = retriever.search(max_results=1)

    # Should have returned empty list due to caught exception
    assert results == []

    # The streamer must have received an error message containing the exception text
    assert any("Error in MCP search" in msg and "forced failure" in msg for msg in retriever.streamer.logged)
