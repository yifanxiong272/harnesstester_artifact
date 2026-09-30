import asyncio
import types
import pytest

from gpt_researcher.retrievers.mcp.retriever import MCPRetriever


class DummyStreamer:
    def __init__(self):
        self.logs = []

    def stream_log_sync(self, message: str):
        # Capture sync-streamed messages for assertions
        self.logs.append(message)


@pytest.mark.parametrize("max_results", [1, 3])
def test_no_mcp_configs_round_018(max_results):
    """
    When there are no mcp_configs the method should log via streamer and return an empty list.
    """
    # Create instance without calling __init__ to control internals deterministically
    inst = object.__new__(MCPRetriever)
    inst.mcp_configs = []  # no configs triggers early return
    inst.query = "test"
    inst.streamer = DummyStreamer()

    results = MCPRetriever.search(inst, max_results=max_results)

    assert results == []
    # Ensure streamer was informed with the expected high-level message
    assert any("MCP retriever cannot proceed" in msg or "MCP retriever cannot proceed" in msg for msg in inst.streamer.logs)


def test_search_async_runs_via_asyncio_run_round_018(monkeypatch):
    """
    If no running event loop is detected (get_running_loop raises RuntimeError),
    search should use asyncio.run and return the coroutine's result.
    """
    inst = object.__new__(MCPRetriever)
    inst.mcp_configs = [{"url": "http://dummy"}]
    inst.query = "query"
    inst.streamer = DummyStreamer()

    async def fake_search(max_results):
        # simple deterministic async result
        return [{"id": f"r{max_results}", "score": "1.0"}]

    inst.search_async = types.MethodType(lambda self, max_results: fake_search(max_results), inst)

    # Force no running loop to exercise the asyncio.run path
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: (_ for _ in ()).throw(RuntimeError("no loop")))

    results = MCPRetriever.search(inst, max_results=2)

    assert isinstance(results, list)
    assert results == [{"id": "r2", "score": "1.0"}]
    # No error logs expected in streamer for successful run
    assert inst.streamer.logs == []


def test_search_async_runs_in_thread_round_018(monkeypatch):
    """
    Simulate being inside an async context by having asyncio.get_running_loop return a dummy object.
    Ensure the code uses the thread-run path and returns the expected results.
    """
    inst = object.__new__(MCPRetriever)
    inst.mcp_configs = [{"url": "http://dummy"}]
    inst.query = "query-thread"
    inst.streamer = DummyStreamer()

    async def fake_search(max_results):
        # emulate IO-bound work but return immediately
        return [{"id": f"thread-{max_results}"}]

    inst.search_async = types.MethodType(lambda self, max_results: fake_search(max_results), inst)

    # Simulate that we're in an async context
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: object())

    # Ensure cleanup path doesn't try to iterate pending tasks in a complicated way
    monkeypatch.setattr(asyncio, "all_tasks", lambda loop=None: set())

    # Speed up sleeps used during cleanup
    monkeypatch.setattr("time.sleep", lambda s: None)

    results = MCPRetriever.search(inst, max_results=5)

    assert results == [{"id": "thread-5"}]
    assert inst.streamer.logs == []


def test_search_async_raises_and_outer_exception_handled_round_018(monkeypatch):
    """
    If the async search raises, the outer try/except should catch it,
    log via streamer.stream_log_sync, and return an empty list.
    """
    inst = object.__new__(MCPRetriever)
    inst.mcp_configs = [{"url": "http://dummy"}]
    inst.query = "bomb"
    inst.streamer = DummyStreamer()

    async def exploding_search(max_results):
        raise RuntimeError("boom-boom")

    inst.search_async = types.MethodType(lambda self, max_results: exploding_search(max_results), inst)

    # Force the asyncio.run path to trigger the exception from the coroutine
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: (_ for _ in ()).throw(RuntimeError("no loop")))

    results = MCPRetriever.search(inst, max_results=1)

    assert results == []

    # Check that the streamer received an error message about the MCP search failure
    assert any("Error in MCP search" in msg or "Error in MCP search" in msg for msg in inst.streamer.logs)
