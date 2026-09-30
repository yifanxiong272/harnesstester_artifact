# file: gpt_researcher/mcp/client.py:105-136
# asked: {"lines": [105, 112, 113, 114, 116, 117, 118, 120, 121, 122, 124, 126, 127, 130, 132, 134, 135, 136], "branches": [[113, 114], [113, 116], [116, 117], [116, 120], [120, 121], [120, 124]]}
# gained: {"lines": [105, 112, 113, 114, 116, 117, 118, 120, 121, 122, 124, 126, 127, 130, 132, 134, 135, 136], "branches": [[113, 114], [113, 116], [116, 117], [116, 120], [120, 121], [120, 124]]}

import asyncio
import importlib
import types
import pytest

client_mod = importlib.import_module("gpt_researcher.mcp.client")
MCPClientManager = client_mod.MCPClientManager


@pytest.mark.asyncio
async def test_returns_existing_client_without_creating(monkeypatch):
    # Prepare a manager instance without calling its constructor
    mgr = object.__new__(MCPClientManager)
    mgr._client_lock = asyncio.Lock()
    existing = object()
    mgr._client = existing

    # Ensure module-level flags won't interfere
    monkeypatch.setattr(client_mod, "HAS_MCP_ADAPTERS", False)
    # Set methods that would be called if not returning early to ones that fail if invoked
    mgr.convert_configs_to_langchain_format = lambda: (_ for _ in ()).throw(
        AssertionError("convert should not be called when _client exists")
    )

    res = await mgr.get_or_create_client()
    assert res is existing
    # confirm _client unchanged
    assert mgr._client is existing


@pytest.mark.asyncio
async def test_returns_none_when_adapter_missing(monkeypatch):
    mgr = object.__new__(MCPClientManager)
    mgr._client_lock = asyncio.Lock()
    mgr._client = None
    mgr.mcp_configs = ["cfg1"]  # non-empty, but adapters missing

    # Spy on logger.error
    recorded = {"msg": None}

    def fake_error(msg):
        recorded["msg"] = msg

    monkeypatch.setattr(client_mod, "HAS_MCP_ADAPTERS", False)
    monkeypatch.setattr(client_mod, "logger", types.SimpleNamespace(error=fake_error, info=lambda m: None), raising=False)
    res = await mgr.get_or_create_client()
    assert res is None
    assert recorded["msg"] is not None
    assert "not installed" in recorded["msg"] or "langchain-mcp-adapters" in recorded["msg"]


@pytest.mark.asyncio
async def test_returns_none_when_no_configs(monkeypatch):
    mgr = object.__new__(MCPClientManager)
    mgr._client_lock = asyncio.Lock()
    mgr._client = None
    mgr.mcp_configs = []  # empty configs

    recorded = {"msg": None}

    def fake_error(msg):
        recorded["msg"] = msg

    monkeypatch.setattr(client_mod, "HAS_MCP_ADAPTERS", True)
    monkeypatch.setattr(client_mod, "logger", types.SimpleNamespace(error=fake_error, info=lambda m: None), raising=False)

    res = await mgr.get_or_create_client()
    assert res is None
    assert recorded["msg"] is not None
    assert "No MCP server configurations" in recorded["msg"]


@pytest.mark.asyncio
async def test_successful_client_creation_sets_client(monkeypatch):
    mgr = object.__new__(MCPClientManager)
    mgr._client_lock = asyncio.Lock()
    mgr._client = None
    mgr.mcp_configs = ["a", "b"]

    # convert returns a list of server configs (langchain format)
    def convert():
        return [{"name": "s1"}, {"name": "s2"}]

    mgr.convert_configs_to_langchain_format = convert

    # Dummy MultiServerMCPClient that stores what it was created with
    class DummyClient:
        def __init__(self, server_configs):
            self.server_configs = server_configs

    monkeypatch.setattr(client_mod, "HAS_MCP_ADAPTERS", True)
    # Use raising=False in case the attribute wasn't imported into the module namespace
    monkeypatch.setattr(client_mod, "MultiServerMCPClient", DummyClient, raising=False)

    # Spy info log
    recorded_info = {"msg": None}

    def fake_info(msg):
        recorded_info["msg"] = msg

    monkeypatch.setattr(client_mod, "logger", types.SimpleNamespace(info=fake_info, error=lambda m: None), raising=False)

    res = await mgr.get_or_create_client()
    assert isinstance(res, DummyClient)
    assert res is mgr._client
    assert len(res.server_configs) == 2
    assert "Creating MCP client for 2 server(s)" in (recorded_info["msg"] or "")


@pytest.mark.asyncio
async def test_exception_creating_client_returns_none_and_logs(monkeypatch):
    mgr = object.__new__(MCPClientManager)
    mgr._client_lock = asyncio.Lock()
    mgr._client = None
    mgr.mcp_configs = ["cfg"]

    # convert returns configs but MultiServerMCPClient will raise
    def convert():
        return [{"name": "only"}]

    mgr.convert_configs_to_langchain_format = convert

    def raising_ctor(_):
        raise RuntimeError("boom")

    recorded = {"msg": None}

    def fake_error(msg):
        recorded["msg"] = msg

    monkeypatch.setattr(client_mod, "HAS_MCP_ADAPTERS", True)
    monkeypatch.setattr(client_mod, "MultiServerMCPClient", raising_ctor, raising=False)
    monkeypatch.setattr(client_mod, "logger", types.SimpleNamespace(error=fake_error, info=lambda m: None), raising=False)

    res = await mgr.get_or_create_client()
    assert res is None
    assert recorded["msg"] is not None
    assert "Error creating MCP client" in recorded["msg"]
