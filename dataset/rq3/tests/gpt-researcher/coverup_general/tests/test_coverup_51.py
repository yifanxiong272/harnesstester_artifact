# file: gpt_researcher/mcp/client.py:105-136
# asked: {"lines": [105, 112, 113, 114, 116, 117, 118, 120, 121, 122, 124, 126, 127, 130, 132, 134, 135, 136], "branches": [[113, 114], [113, 116], [116, 117], [116, 120], [120, 121], [120, 124]]}
# gained: {"lines": [105, 112, 113, 114, 116, 117, 118, 120, 121, 122, 124, 126, 127, 130, 132, 134, 135, 136], "branches": [[113, 114], [113, 116], [116, 117], [116, 120], [120, 121], [120, 124]]}

import asyncio
import importlib
import pytest

pytestmark = pytest.mark.asyncio


class DummyLogger:
    def __init__(self):
        self.info_calls = []
        self.error_calls = []

    def info(self, *args, **kwargs):
        self.info_calls.append((args, kwargs))

    def error(self, *args, **kwargs):
        self.error_calls.append((args, kwargs))


async def _call_get_or_create(manager):
    return await manager.get_or_create_client()


def _import_module():
    return importlib.import_module("gpt_researcher.mcp.client")


async def test_returns_existing_client(monkeypatch):
    client_module = _import_module()
    monkeypatch.setattr(client_module, "HAS_MCP_ADAPTERS", True)
    dummy_logger = DummyLogger()
    monkeypatch.setattr(client_module, "logger", dummy_logger)

    manager = client_module.MCPClientManager(mcp_configs=[{"url": "http://x"}])
    sentinel = object()
    manager._client = sentinel

    result = await manager.get_or_create_client()
    assert result is sentinel
    assert dummy_logger.error_calls == []
    assert dummy_logger.info_calls == []


async def test_no_adapters_returns_none(monkeypatch):
    client_module = _import_module()
    monkeypatch.setattr(client_module, "HAS_MCP_ADAPTERS", False)
    dummy_logger = DummyLogger()
    monkeypatch.setattr(client_module, "logger", dummy_logger)

    manager = client_module.MCPClientManager(mcp_configs=[{"url": "http://x"}])

    result = await manager.get_or_create_client()
    assert result is None
    assert len(dummy_logger.error_calls) == 1
    assert "langchain-mcp-adapters not installed" in " ".join(map(str, dummy_logger.error_calls[0][0]))


async def test_no_configs_returns_none(monkeypatch):
    client_module = _import_module()
    monkeypatch.setattr(client_module, "HAS_MCP_ADAPTERS", True)
    dummy_logger = DummyLogger()
    monkeypatch.setattr(client_module, "logger", dummy_logger)

    manager = client_module.MCPClientManager(mcp_configs=[])

    result = await manager.get_or_create_client()
    assert result is None
    assert len(dummy_logger.error_calls) == 1
    assert "No MCP server configurations found" in " ".join(map(str, dummy_logger.error_calls[0][0]))


async def test_convert_raises_returns_none(monkeypatch):
    client_module = _import_module()
    monkeypatch.setattr(client_module, "HAS_MCP_ADAPTERS", True)
    dummy_logger = DummyLogger()
    monkeypatch.setattr(client_module, "logger", dummy_logger)

    manager = client_module.MCPClientManager(mcp_configs=[{"url": "http://x"}])

    # Patch convert_configs_to_langchain_format to raise synchronously
    def raise_conversion():
        raise RuntimeError("conversion failed")

    monkeypatch.setattr(manager, "convert_configs_to_langchain_format", raise_conversion)

    result = await manager.get_or_create_client()
    assert result is None
    assert any("Error creating MCP client" in " ".join(map(str, call[0])) or "conversion failed" in " ".join(map(str, call[0])) for call in dummy_logger.error_calls)


async def test_successful_creation_and_caching(monkeypatch):
    client_module = _import_module()
    monkeypatch.setattr(client_module, "HAS_MCP_ADAPTERS", True)
    dummy_logger = DummyLogger()
    monkeypatch.setattr(client_module, "logger", dummy_logger)

    fake_server_configs = {"s1": {"url": "http://x", "api_key": "key"}}

    manager = client_module.MCPClientManager(mcp_configs=[{"url": "http://x", "api_key": "key"}])
    monkeypatch.setattr(manager, "convert_configs_to_langchain_format", lambda: fake_server_configs)

    created_args = {}

    class DummyMultiServerClient:
        def __init__(self, configs):
            created_args["configs"] = configs

    # Allow setting even if attribute is not present in the module
    monkeypatch.setattr(client_module, "MultiServerMCPClient", DummyMultiServerClient, raising=False)

    client1 = await manager.get_or_create_client()
    assert isinstance(client1, DummyMultiServerClient)
    assert manager._client is client1
    assert created_args["configs"] is fake_server_configs
    assert any("Creating MCP client" in " ".join(map(str, call[0])) for call in dummy_logger.info_calls)

    dummy_logger.info_calls.clear()
    client2 = await manager.get_or_create_client()
    assert client2 is client1
    assert dummy_logger.info_calls == []
