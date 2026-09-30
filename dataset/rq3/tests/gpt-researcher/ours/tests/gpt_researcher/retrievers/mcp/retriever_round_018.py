import asyncio
import time
import types

import pytest

import gpt_researcher.retrievers.mcp.retriever as retriever_mod
from gpt_researcher.retrievers.mcp.retriever import MCPRetriever


class DummyStreamer:
    def __init__(self):
        self.messages = []

    def stream_log_sync(self, msg: str):
        self.messages.append(msg)


class DummyLogger:
    def __init__(self):
        self.errors = []
        self.infos = []
        self.debugs = []

    def error(self, msg: str):
        self.errors.append(msg)

    def info(self, msg: str):
        self.infos.append(msg)

    def debug(self, msg: str):
        self.debugs.append(msg)


def make_bare_retriever_with(attrs: dict):
    # Create instance without invoking __init__ to control attributes precisely
    inst = object.__new__(MCPRetriever)
    for k, v in attrs.items():
        setattr(inst, k, v)
    return inst


def test_search_no_configs_round_018():
    """
    When mcp_configs is falsy, search should log an error via streamer and return empty list.
    Covers the branch where the method returns early due to missing configs.
    """
    dummy_streamer = DummyStreamer()
    dummy_logger = DummyLogger()

    # Patch the module logger so calls are captured (no real logging side-effects)
    retriever_mod.logger = dummy_logger

    inst = make_bare_retriever_with({
        "mcp_configs": [],
        "streamer": dummy_streamer,
        "query": "test-query-no-config",
    })

    results = inst.search(max_results=3)

    assert results == [], "Expected empty results when no mcp_configs are provided"
    # Ensure streamer was used to stream a user-facing log
    assert any("MCP retriever cannot proceed" in m for m in dummy_streamer.messages), (
        "Expected streamer to receive a user-facing error message"
    )
    # The module logger.error should have been called with the expected message
    assert any("No MCP server configurations available" in e for e in dummy_logger.errors)


def test_search_pending_cleanup_round_018(monkeypatch):
    """
    When an event loop is detected (async context), ensure the code runs the threaded
    run_in_thread path and correctly returns results while attempting cleanup of pending tasks.

    We patch asyncio.get_running_loop to force the branch that runs the search in a separate
    event loop thread, and patch asyncio.wait_for to immediately raise TimeoutError so
    the branch that handles task cleanup timeout is exercised deterministically and quickly.
    """
    dummy_streamer = DummyStreamer()
    dummy_logger = DummyLogger()

    # Patch module logger to capture info/debug calls
    retriever_mod.logger = dummy_logger

    # Force the codepath that assumes an event loop is running
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: object())

    # Make wait_for raise TimeoutError immediately to exercise the timeout branch without delay
    original_wait_for = asyncio.wait_for

    def fake_wait_for(coro_or_future, timeout):
        raise asyncio.TimeoutError()

    monkeypatch.setattr(asyncio, "wait_for", fake_wait_for)

    # Also avoid actual sleeping delays in cleanup by patching time.sleep to no-op
    monkeypatch.setattr(time, "sleep", lambda s: None)

    inst = make_bare_retriever_with({
        "mcp_configs": ["config1"],
        "streamer": dummy_streamer,
        "query": "test-query-pending",
    })

    # Define an async search_async that spawns a background (pending) task and returns a result
    async def fake_search_async(self, max_results):
        # Spawn a background task that will be pending at cleanup time
        # This task sleeps for a while; because wait_for is patched to raise, cleanup will not block
        asyncio.create_task(asyncio.sleep(10))
        return [{"id": "r1", "score": "0.9"}]

    # Bind the coroutine as a method on the instance
    inst.search_async = types.MethodType(fake_search_async, inst)

    # Execute the synchronous wrapper. This will use ThreadPoolExecutor and our patched wait_for
    results = inst.search(max_results=1)

    # Verify the returned results come from our fake_search_async
    assert results == [{"id": "r1", "score": "0.9"}]

    # Ensure an info log was emitted with the query to show the normal progressing branch executed
    assert any("test-query-pending" in msg for msg in dummy_logger.infos), (
        "Expected logger.info to be called with the query"
    )

    # Cleanup: restore any monkeypatched globals (pytest's monkeypatch fixture will handle this)
    monkeypatch.setattr(asyncio, "wait_for", original_wait_for)
