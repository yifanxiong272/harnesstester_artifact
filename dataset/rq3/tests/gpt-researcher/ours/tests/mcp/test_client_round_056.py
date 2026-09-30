import asyncio
import pytest

import gpt_researcher.mcp.client as client_mod

# Helper logger stub to capture messages deterministically
class LoggerStub:
    def __init__(self):
        self.errors = []
        self.infos = []

    def error(self, msg, *args, **kwargs):
        # store formatted message for deterministic assertions
        try:
            self.errors.append(msg.format(*args) if args else str(msg))
        except Exception:
            self.errors.append(str(msg))

    def info(self, msg, *args, **kwargs):
        try:
            self.infos.append(msg.format(*args) if args else str(msg))
        except Exception:
            self.infos.append(str(msg))


@pytest.mark.asyncio
async def test_returns_existing_client_round_056():
    # Ensure early-return when _client already set
    mgr = client_mod.MCPClientManager(mcp_configs=[{"dummy": True}])
    sentinel = object()
    mgr._client = sentinel

    # Ensure lock exists; if not, provide one
    if not hasattr(mgr, "_client_lock") or mgr._client_lock is None:
        mgr._client_lock = asyncio.Lock()

    res = await mgr.get_or_create_client()
    assert res is sentinel


@pytest.mark.asyncio
async def test_missing_adapters_returns_none_round_056(monkeypatch):
    # Configure environment: adapters not installed
    monkeypatch.setattr(client_mod, "HAS_MCP_ADAPTERS", False)

    logger = LoggerStub()
    monkeypatch.setattr(client_mod, "logger", logger)

    mgr = client_mod.MCPClientManager(mcp_configs=[{"server": 1}])
    if not hasattr(mgr, "_client_lock") or mgr._client_lock is None:
        mgr._client_lock = asyncio.Lock()

    got = await mgr.get_or_create_client()
    assert got is None
    # confirm the logged error message was emitted
    assert any("langchain-mcp-adapters not installed" in e for e in logger.errors)


@pytest.mark.asyncio
async def test_no_configs_returns_none_round_056(monkeypatch):
    # Adapters present but no server configs -> early None with specific log
    monkeypatch.setattr(client_mod, "HAS_MCP_ADAPTERS", True)
    logger = LoggerStub()
    monkeypatch.setattr(client_mod, "logger", logger)

    mgr = client_mod.MCPClientManager(mcp_configs=[])
    if not hasattr(mgr, "_client_lock") or mgr._client_lock is None:
        mgr._client_lock = asyncio.Lock()

    got = await mgr.get_or_create_client()
    assert got is None
    assert any("No MCP server configurations found" in e for e in logger.errors)


@pytest.mark.asyncio
async def test_successful_creation_round_056(monkeypatch):
    # Happy path: convert configs -> langchain format -> MultiServerMCPClient created
    monkeypatch.setattr(client_mod, "HAS_MCP_ADAPTERS", True)

    # Prepare fake server configs returned by convert method
    fake_converted = [{"host": "h1"}, {"host": "h2"}]

    # Replace MultiServerMCPClient with a deterministic stub that records arguments
    created_args = {}

    class DummyMultiServerMCPClient:
        def __init__(self, configs):
            created_args['configs'] = configs
            # provide some trivial behavior/property
            self.count = len(configs)

    monkeypatch.setattr(client_mod, "MultiServerMCPClient", DummyMultiServerMCPClient)

    # Capture logger.info
    logger = LoggerStub()
    monkeypatch.setattr(client_mod, "logger", logger)

    # Create manager and patch its converter method to return fake_converted
    mgr = client_mod.MCPClientManager(mcp_configs=[{"raw": 1}])
    if not hasattr(mgr, "_client_lock") or mgr._client_lock is None:
        mgr._client_lock = asyncio.Lock()

    # Patch the instance method convert_configs_to_langchain_format
    async_convert = None
    def fake_convert():
        return fake_converted

    monkeypatch.setattr(mgr, "convert_configs_to_langchain_format", fake_convert)

    got = await mgr.get_or_create_client()
    # Should return the DummyMultiServerMCPClient instance
    assert isinstance(got, DummyMultiServerMCPClient)
    assert got is mgr._client
    # confirm the stub got the converted configs
    assert created_args['configs'] is fake_converted
    # logger.info should mention number of servers
    assert any("Creating MCP client for 2 server(s)" in s for s in logger.infos)


@pytest.mark.asyncio
async def test_exception_in_creation_returns_none_round_056(monkeypatch):
    # If constructing the client raises, get_or_create_client should catch and return None
    monkeypatch.setattr(client_mod, "HAS_MCP_ADAPTERS", True)

    def raising_convert():
        return [{"host": "x"}]

    class RaisingClient:
        def __init__(self, configs):
            raise RuntimeError("boom")

    monkeypatch.setattr(client_mod, "MultiServerMCPClient", RaisingClient)
    logger = LoggerStub()
    monkeypatch.setattr(client_mod, "logger", logger)

    mgr = client_mod.MCPClientManager(mcp_configs=[{"raw": 1}])
    if not hasattr(mgr, "_client_lock") or mgr._client_lock is None:
        mgr._client_lock = asyncio.Lock()

    monkeypatch.setattr(mgr, "convert_configs_to_langchain_format", raising_convert)

    got = await mgr.get_or_create_client()
    assert got is None
    assert any("Error creating MCP client" in e for e in logger.errors)
