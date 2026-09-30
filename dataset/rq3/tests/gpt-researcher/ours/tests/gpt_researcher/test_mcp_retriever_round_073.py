import asyncio
from types import SimpleNamespace

from gpt_researcher.retrievers.mcp import retriever


class _AsyncRecorder:
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


class _DummyLogger:
    def __init__(self):
        self.errs = []

    def error(self, msg):
        # mimic logger.error signature
        self.errs.append(msg)


def _make_instance():
    # Create MCPRetriever instance without running its __init__
    inst = object.__new__(retriever.MCPRetriever)
    # default attributes that _get_all_tools expects
    inst._all_tools_cache = None
    inst.client_manager = SimpleNamespace()
    inst.streamer = _AsyncRecorder()
    return inst


def test_get_all_tools_cache_hit_round_073():
    inst = _make_instance()
    # When cache is present, the method should return it immediately
    inst._all_tools_cache = ["cached_tool"]

    async def bad_get_all_tools():
        raise AssertionError("client_manager.get_all_tools should not be called when cache is present")

    inst.client_manager.get_all_tools = bad_get_all_tools

    result = asyncio.run(inst._get_all_tools())
    assert result == ["cached_tool"]
    # ensure streamer was not used
    assert inst.streamer.logs == []
    assert inst.streamer.warnings == []
    assert inst.streamer.errors == []


def test_get_all_tools_loaded_non_empty_round_073():
    inst = _make_instance()

    async def get_all_tools():
        return ["tool1", "tool2"]

    inst.client_manager.get_all_tools = get_all_tools

    result = asyncio.run(inst._get_all_tools())
    # Should return the list from client and cache it
    assert result == ["tool1", "tool2"]
    assert inst._all_tools_cache == ["tool1", "tool2"]
    # Streamer should have been called with a message containing the loaded count
    assert len(inst.streamer.logs) == 1
    assert "Loaded 2 total tools from MCP servers" in inst.streamer.logs[0]


def test_get_all_tools_loaded_empty_round_073():
    inst = _make_instance()

    async def get_all_tools():
        return []

    inst.client_manager.get_all_tools = get_all_tools

    result = asyncio.run(inst._get_all_tools())
    # Should return empty list and not set cache
    assert result == []
    assert inst._all_tools_cache is None
    # Streamer warning should be triggered
    assert inst.streamer.warnings == ["No tools available from MCP servers"]


def test_get_all_tools_exception_round_073():
    inst = _make_instance()

    async def get_all_tools():
        raise Exception("boom")

    inst.client_manager.get_all_tools = get_all_tools

    # Patch module-level logger to capture the error call
    original_logger = getattr(retriever, "logger", None)
    dummy_logger = _DummyLogger()
    retriever.logger = dummy_logger

    try:
        result = asyncio.run(inst._get_all_tools())
    finally:
        # restore original logger to avoid side effects for other tests
        if original_logger is not None:
            retriever.logger = original_logger

    # On exception, method should return empty list
    assert result == []
    # Logger.error should have been invoked with a message including the exception
    assert any("Error getting MCP tools" in m for m in dummy_logger.errs)
    # Streamer.error should be awaited with the exception string
    assert inst.streamer.errors == ["Error getting MCP tools: boom"]
