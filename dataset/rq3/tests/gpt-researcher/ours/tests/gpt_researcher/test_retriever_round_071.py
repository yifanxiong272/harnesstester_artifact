import pytest

from gpt_researcher.retrievers.mcp import retriever as retriever_mod

# Dummy collaborator implementations to patch into the module under test
class DummyClientManager:
    def __init__(self, mcp_configs):
        # record what was passed in
        self.init_arg = mcp_configs


class DummyToolSelector:
    def __init__(self, cfg, researcher):
        self.cfg = cfg
        self.researcher = researcher


class DummyResearchSkill:
    def __init__(self, cfg, researcher):
        self.cfg = cfg
        self.researcher = researcher


class DummyStreamer:
    def __init__(self, websocket):
        # record websocket and all messages streamed
        self.websocket = websocket
        self.streamed = []

    def stream_log_sync(self, msg):
        self.streamed.append(msg)


class DummyLogger:
    def __init__(self):
        self.errors = []

    def error(self, msg):
        self.errors.append(msg)


def _patch_common(monkeypatch, mcp_configs_return, cfg_return):
    """Patch the module-level collaborators and MCPRetriever helpers.

    Returns: (DummyLogger instance, DummyStreamer class)
    """
    # Patch the external classes used in __init__ where the code resolves them
    monkeypatch.setattr(retriever_mod, "MCPClientManager", DummyClientManager)
    monkeypatch.setattr(retriever_mod, "MCPToolSelector", DummyToolSelector)
    monkeypatch.setattr(retriever_mod, "MCPResearchSkill", DummyResearchSkill)
    monkeypatch.setattr(retriever_mod, "MCPStreamer", DummyStreamer)

    # Patch logger on the module so we can observe error calls
    dummy_logger = DummyLogger()
    monkeypatch.setattr(retriever_mod, "logger", dummy_logger)

    # Patch MCPRetriever._get_mcp_configs and _get_config to deterministic returns
    monkeypatch.setattr(
        retriever_mod.MCPRetriever,
        "_get_mcp_configs",
        lambda self: mcp_configs_return,
    )
    monkeypatch.setattr(
        retriever_mod.MCPRetriever,
        "_get_config",
        lambda self: cfg_return,
    )

    return dummy_logger


def test_init_with_configs_round_071(monkeypatch):
    """When mcp_configs is non-empty, the streamer should log initialization messages

    This covers the branch where self.mcp_configs is truthy (lines 84-86).
    """
    # Prepare module patches to simulate one MCP config and a config dict
    mcp_configs = [{"url": "http://mcp.test"}, {"url": "http://mcp2.test"}]
    cfg = {"some": "cfg"}
    dummy_logger = _patch_common(monkeypatch, mcp_configs_return=mcp_configs, cfg_return=cfg)

    # Create a sentinel researcher object to ensure it is passed through
    sentinel_researcher = object()

    # Instantiate the retriever
    r = retriever_mod.MCPRetriever(
        query="search-term",
        headers={"Auth": "token"},
        query_domains=["example.com"],
        websocket="dummy-ws",
        researcher=sentinel_researcher,
    )

    # Basic attribute assertions
    assert r.query == "search-term"
    assert r.headers == {"Auth": "token"}
    assert r.query_domains == ["example.com"]
    assert r.websocket == "dummy-ws"
    assert r.researcher is sentinel_researcher

    # Ensure the client manager got the MCP configs we returned
    assert isinstance(r.client_manager, DummyClientManager)
    assert r.client_manager.init_arg == mcp_configs

    # Tool selector and research skill should be initialized with cfg and researcher
    assert isinstance(r.tool_selector, DummyToolSelector)
    assert r.tool_selector.cfg == cfg
    assert r.tool_selector.researcher is sentinel_researcher

    assert isinstance(r.mcp_researcher, DummyResearchSkill)
    assert r.mcp_researcher.cfg == cfg
    assert r.mcp_researcher.researcher is sentinel_researcher

    # Streamer should have been constructed with provided websocket
    assert isinstance(r.streamer, DummyStreamer)
    assert r.streamer.websocket == "dummy-ws"

    # Because mcp_configs is non-empty, two initialization messages should be streamed
    assert len(r.streamer.streamed) == 2
    # First log should mention the query text
    assert "search-term" in r.streamer.streamed[0]
    # Second log should mention the number of configs we provided
    assert f"Found {len(mcp_configs)} MCP server configurations" in r.streamer.streamed[1]

    # The module logger should have no error calls in this branch
    assert dummy_logger.errors == []


def test_init_no_configs_round_071(monkeypatch):
    """When mcp_configs is empty, logger.error and a CRITICAL streamer message are produced.

    This covers the else branch where self.mcp_configs is falsy (lines 87-89).
    """
    mcp_configs = []
    cfg = {"some": "cfg"}
    dummy_logger = _patch_common(monkeypatch, mcp_configs_return=mcp_configs, cfg_return=cfg)

    # Construct retriever with minimal inputs
    r = retriever_mod.MCPRetriever(query="no-configs-query", headers=None, query_domains=None, websocket=None, researcher=None)

    # When there are no configs, client_manager is still created (with empty list)
    assert isinstance(r.client_manager, DummyClientManager)
    assert r.client_manager.init_arg == []

    # The module logger.error should have been called once with the expected message
    assert len(dummy_logger.errors) == 1
    assert "No MCP server configurations found. The retriever will fail during search." in dummy_logger.errors[0]

    # Streamer should have logged the CRITICAL guidance message
    assert isinstance(r.streamer, DummyStreamer)
    # There should be exactly one streamed message in this branch (the CRITICAL message)
    assert any("CRITICAL" in msg or "CRITICAL:" in msg or "Please check documentation" in msg for msg in r.streamer.streamed)
