# file: gpt_researcher/retrievers/mcp/retriever.py:44-89
# asked: {"lines": [44, 46, 47, 48, 49, 50, 64, 65, 66, 67, 68, 71, 72, 75, 76, 77, 78, 81, 84, 85, 86, 88, 89], "branches": [[84, 85], [84, 88]]}
# gained: {"lines": [44, 47, 48, 49, 50, 64, 65, 66, 67, 68, 71, 72, 75, 76, 77, 78, 81, 84, 85, 86, 88, 89], "branches": [[84, 85], [84, 88]]}

import importlib
import types
import pytest


def _get_retriever_module():
    # try expected module path(s)
    possible = [
        "gpt_researcher.retrievers.mcp.retriever",
        "gpt_researcher.retrievers.mcp.retriever",  # duplicate kept intentionally for clarity
    ]
    for name in possible:
        try:
            return importlib.import_module(name)
        except Exception:
            continue
    raise ImportError("Could not import MCP retriever module from expected locations.")


class StubMCPClientManager:
    def __init__(self, configs):
        self.configs = configs


class StubMCPToolSelector:
    def __init__(self, cfg, researcher):
        self.cfg = cfg
        self.researcher = researcher


class StubMCPResearchSkill:
    def __init__(self, cfg, researcher):
        self.cfg = cfg
        self.researcher = researcher


class StubMCPStreamer:
    def __init__(self, websocket):
        self.websocket = websocket
        self.logs = []

    def stream_log_sync(self, msg):
        # Emulate possible side effects; record messages for assertions
        self.logs.append(msg)


class DummyLogger:
    def __init__(self):
        self.errors = []

    def error(self, msg):
        self.errors.append(msg)


def test_init_with_mcp_configs(monkeypatch):
    mod = _get_retriever_module()
    # Patch external dependencies in the module
    monkeypatch.setattr(mod, "MCPClientManager", StubMCPClientManager)
    monkeypatch.setattr(mod, "MCPToolSelector", StubMCPToolSelector)
    monkeypatch.setattr(mod, "MCPResearchSkill", StubMCPResearchSkill)
    monkeypatch.setattr(mod, "MCPStreamer", StubMCPStreamer)
    dummy_logger = DummyLogger()
    monkeypatch.setattr(mod, "logger", dummy_logger)

    # Ensure _get_mcp_configs returns a non-empty list
    def fake_get_mcp_configs(self):
        return [{"url": "http://a"}, {"url": "http://b"}]

    def fake_get_config(self):
        return {"llm": "cfg"}

    monkeypatch.setattr(mod.MCPRetriever, "_get_mcp_configs", fake_get_mcp_configs)
    monkeypatch.setattr(mod.MCPRetriever, "_get_config", fake_get_config)

    # Instantiate retriever
    Retriever = mod.MCPRetriever
    r = Retriever(query="my query", headers={"h": "v"}, query_domains=["d1"], websocket="ws", researcher=object())

    # Postconditions: streamer should have been called twice with expected substrings
    assert isinstance(r.streamer, StubMCPStreamer)
    assert len(r.streamer.logs) == 2, "Expected two stream_log_sync calls when mcp_configs is non-empty"
    assert any("Initializing MCP retriever for query: my query" in msg or "Initializing MCP retriever for query" in msg for msg in r.streamer.logs)
    assert any("Found 2 MCP server configurations" in msg or "Found 2 MCP server configurations" in msg for msg in r.streamer.logs)

    # logger.error should not have been called
    assert dummy_logger.errors == [], "logger.error should not be called when mcp_configs is present"


def test_init_without_mcp_configs(monkeypatch):
    mod = _get_retriever_module()
    # Patch external dependencies in the module
    monkeypatch.setattr(mod, "MCPClientManager", StubMCPClientManager)
    monkeypatch.setattr(mod, "MCPToolSelector", StubMCPToolSelector)
    monkeypatch.setattr(mod, "MCPResearchSkill", StubMCPResearchSkill)
    monkeypatch.setattr(mod, "MCPStreamer", StubMCPStreamer)
    dummy_logger = DummyLogger()
    monkeypatch.setattr(mod, "logger", dummy_logger)

    # Ensure _get_mcp_configs returns an empty list
    def fake_get_mcp_configs_empty(self):
        return []

    def fake_get_config(self):
        return {"llm": "cfg"}

    monkeypatch.setattr(mod.MCPRetriever, "_get_mcp_configs", fake_get_mcp_configs_empty)
    monkeypatch.setattr(mod.MCPRetriever, "_get_config", fake_get_config)

    # Instantiate retriever
    Retriever = mod.MCPRetriever
    r = Retriever(query="another query", websocket=None, researcher=object())

    # Postconditions: logger.error called and critical stream message sent
    assert isinstance(r.streamer, StubMCPStreamer)
    # Should have at least one log entry with CRITICAL message
    assert any("CRITICAL" in msg or "CRITICAL" in msg.upper() for msg in r.streamer.logs), "Expected a CRITICAL stream log when no mcp_configs"
    # Check logger recorded an error about no MCP server configurations
    assert any("No MCP server configurations found" in err for err in dummy_logger.errors), "Expected logger.error to be called with missing MCP configs message"
