# file: gpt_researcher/retrievers/mcp/retriever.py:300-324
# asked: {"lines": [300, 307, 308, 310, 311, 313, 314, 315, 316, 318, 319, 321, 322, 323, 324], "branches": [[307, 308], [307, 310], [313, 314], [313, 318]]}
# gained: {"lines": [300, 307, 308, 310, 311, 313, 314, 315, 316, 318, 319, 321, 322, 323, 324], "branches": [[307, 308], [307, 310], [313, 314], [313, 318]]}

import pytest
import asyncio

from gpt_researcher.retrievers.mcp.retriever import MCPRetriever


class DummyStreamer:
    def __init__(self):
        self.logs = []
        self.warnings = []
        self.errors = []

    async def stream_log(self, msg):
        self.logs.append(msg)

    async def stream_warning(self, msg):
        self.warnings.append(msg)

    async def stream_error(self, msg):
        self.errors.append(msg)

    # some code paths in the real class may call sync logging during init;
    # provide a no-op sync method to be safe in case it's used elsewhere.
    def stream_log_sync(self, msg):
        self.logs.append(msg)


class DummyClientManagerReturn:
    def __init__(self, return_value):
        self.return_value = return_value
        self.called = 0

    async def get_all_tools(self):
        self.called += 1
        return self.return_value


class DummyClientManagerRaise:
    def __init__(self, exc):
        self.exc = exc
        self.called = 0

    async def get_all_tools(self):
        self.called += 1
        raise self.exc


@pytest.mark.asyncio
async def test_get_all_tools_returns_cache_only():
    # Create instance without running __init__
    retriever = object.__new__(MCPRetriever)
    # Set a cached value; client_manager.get_all_tools should NOT be called
    retriever._all_tools_cache = ["cached_tool"]
    # Client manager that would raise if called
    class BadClient:
        async def get_all_tools(self):
            raise AssertionError("get_all_tools should not be called when cache is present")
    retriever.client_manager = BadClient()
    retriever.streamer = DummyStreamer()

    result = await retriever._get_all_tools()
    assert result == ["cached_tool"]
    # Ensure streamer was not used for logging in this branch
    assert retriever.streamer.logs == []
    assert retriever.streamer.warnings == []
    assert retriever.streamer.errors == []


@pytest.mark.asyncio
async def test_get_all_tools_returns_and_caches_non_empty_list():
    retriever = object.__new__(MCPRetriever)
    retriever._all_tools_cache = None
    tools = [{"name": "t1"}, {"name": "t2"}]
    client = DummyClientManagerReturn(return_value=tools)
    retriever.client_manager = client
    streamer = DummyStreamer()
    retriever.streamer = streamer

    result = await retriever._get_all_tools()
    assert result == tools
    # After successful load, cache should be set
    assert retriever._all_tools_cache is tools
    # client manager should have been called exactly once
    assert client.called == 1
    # stream_log should have been called with a message about loaded tools
    assert len(streamer.logs) == 1
    assert "Loaded" in streamer.logs[0] or "Loaded" in streamer.logs[0]  # defensive check
    # No warnings or errors for successful path
    assert streamer.warnings == []
    assert streamer.errors == []


@pytest.mark.asyncio
async def test_get_all_tools_empty_list_calls_warning_and_returns_empty():
    retriever = object.__new__(MCPRetriever)
    retriever._all_tools_cache = None
    client = DummyClientManagerReturn(return_value=[])
    retriever.client_manager = client
    streamer = DummyStreamer()
    retriever.streamer = streamer

    result = await retriever._get_all_tools()
    assert result == []
    # Cache should remain unset (None) because empty list is falsy and not cached
    assert retriever._all_tools_cache is None
    # client manager called once
    assert client.called == 1
    # Streamer should have one warning about no tools available
    assert len(streamer.warnings) == 1
    assert "No tools available" in streamer.warnings[0]
    # No logs or errors
    assert streamer.logs == []
    assert streamer.errors == []


@pytest.mark.asyncio
async def test_get_all_tools_exception_calls_stream_error_and_returns_empty():
    retriever = object.__new__(MCPRetriever)
    retriever._all_tools_cache = None
    client = DummyClientManagerRaise(exc=RuntimeError("boom"))
    retriever.client_manager = client
    streamer = DummyStreamer()
    retriever.streamer = streamer

    result = await retriever._get_all_tools()
    assert result == []
    # client manager should have been called and raised
    assert client.called == 1
    # stream_error should have been called with the exception message
    assert len(streamer.errors) == 1
    assert "boom" in streamer.errors[0]
    # No logs or warnings for exception path
    assert streamer.logs == []
    assert streamer.warnings == []
