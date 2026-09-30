# file: gpt_researcher/retrievers/mcp/retriever.py:201-298
# asked: {"lines": [201, 215, 216, 217, 218, 219, 222, 224, 226, 228, 231, 232, 235, 236, 237, 238, 239, 240, 243, 245, 246, 247, 250, 251, 252, 253, 254, 255, 258, 259, 260, 261, 262, 263, 265, 267, 268, 271, 272, 275, 278, 279, 280, 281, 284, 285, 286, 288, 290, 292, 294, 295, 296, 298], "branches": [[215, 216], [215, 222], [246, 247], [246, 250], [250, 251], [250, 265], [278, 0], [278, 279]]}
# gained: {"lines": [201, 215, 216, 217, 218, 219, 222, 224, 226, 228, 231, 232, 235, 236, 237, 238, 239, 240, 243, 245, 246, 250, 265, 267, 268, 271, 272, 275, 278, 279, 284, 285, 286, 288, 290, 292, 294, 295, 296, 298], "branches": [[215, 216], [215, 222], [246, 250], [250, 265], [278, 279]]}

import asyncio
import concurrent.futures
import time
from types import SimpleNamespace
import pytest

from gpt_researcher.retrievers.mcp.retriever import MCPRetriever


class DummyStreamer:
    def __init__(self):
        self.messages = []

    def stream_log_sync(self, msg: str):
        self.messages.append(msg)


def make_instance():
    # Create instance without running __init__
    inst = MCPRetriever.__new__(MCPRetriever)
    # minimal attributes used by search
    inst.query = "test query"
    inst.websocket = None
    inst.researcher = None
    inst.cfg = None
    inst.client_manager = None
    inst.tool_selector = None
    inst.mcp_researcher = None
    inst._all_tools_cache = None
    inst.streamer = DummyStreamer()
    return inst


def test_search_no_configs_returns_empty_and_logs():
    inst = make_instance()
    inst.mcp_configs = []  # Force early exit branch

    # attach a stub search_async to ensure it's not called
    async def search_async_stub(max_results):
        raise AssertionError("search_async should not be called when no mcp_configs")

    inst.search_async = search_async_stub

    results = inst.search(max_results=5)
    assert results == []
    # Ensure the streamer logged the expected early-failure message
    assert any("MCP retriever cannot proceed" in m for m in inst.streamer.messages)


def test_search_runtime_error_calls_asyncio_run(monkeypatch):
    inst = make_instance()
    inst.mcp_configs = [{"host": "dummy"}]  # Non-empty to proceed

    expected = [{"id": "r1"}]

    async def search_async_stub(max_results):
        # simulate some async work
        await asyncio.sleep(0)
        return expected

    inst.search_async = search_async_stub

    # Force get_running_loop to raise RuntimeError to take the asyncio.run branch
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: (_ for _ in ()).throw(RuntimeError()))

    results = inst.search(max_results=3)
    assert results == expected


def test_search_running_loop_creates_thread_and_executes(monkeypatch):
    inst = make_instance()
    inst.mcp_configs = [{"host": "dummy"}]

    expected = [{"id": "threaded"}]

    async def search_async_stub(max_results):
        # small await to ensure coroutine behavior
        await asyncio.sleep(0)
        return expected

    inst.search_async = search_async_stub

    # Simulate an active running loop by returning a dummy object (not raising)
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: object())

    results = inst.search(max_results=2)
    assert results == expected


def test_search_get_running_loop_raises_other_exception_triggers_outer_except(monkeypatch):
    inst = make_instance()
    inst.mcp_configs = [{"host": "dummy"}]

    async def search_async_stub(max_results):
        # Should not be reached in this test
        await asyncio.sleep(0)
        return [{"id": "should_not"}]

    inst.search_async = search_async_stub

    # Make get_running_loop raise a non-RuntimeError exception to hit outer except
    def raise_value_error():
        raise ValueError("boom")

    monkeypatch.setattr(asyncio, "get_running_loop", raise_value_error)

    results = inst.search(max_results=1)
    assert results == []
    # Ensure the streamer logged the error message
    assert any("Error in MCP search" in m or "❌ Error in MCP search" in m for m in inst.streamer.messages)
