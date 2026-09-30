import asyncio
import logging
import pytest

from gpt_researcher.mcp.client import MCPClientManager


@pytest.mark.asyncio
async def test_get_all_tools_client_none_round_075(monkeypatch):
    """When get_or_create_client returns None, get_all_tools should return an empty list."""

    async def fake_get_or_create_client(self):
        return None

    monkeypatch.setattr(MCPClientManager, "get_or_create_client", fake_get_or_create_client)

    manager = MCPClientManager([])
    result = await manager.get_all_tools()
    assert result == []


@pytest.mark.asyncio
async def test_get_all_tools_with_tools_round_075(monkeypatch, caplog):
    """When client.get_tools returns a non-empty list, that list should be returned and an info log emitted."""

    class FakeClient:
        async def get_tools(self):
            return [{"name": "tool1"}, {"name": "tool2"}]

    async def fake_get_or_create_client(self):
        return FakeClient()

    monkeypatch.setattr(MCPClientManager, "get_or_create_client", fake_get_or_create_client)

    manager = MCPClientManager([])
    caplog.set_level(logging.INFO)
    result = await manager.get_all_tools()

    assert isinstance(result, list)
    assert result == [{"name": "tool1"}, {"name": "tool2"}]
    # Ensure the informational log about loaded tools appears
    assert "Loaded 2 total tools from MCP servers" in caplog.text


@pytest.mark.asyncio
async def test_get_all_tools_empty_tools_round_075(monkeypatch, caplog):
    """When client.get_tools returns an empty list, get_all_tools returns [] and logs a warning."""

    class FakeClientEmpty:
        async def get_tools(self):
            return []

    async def fake_get_or_create_client(self):
        return FakeClientEmpty()

    monkeypatch.setattr(MCPClientManager, "get_or_create_client", fake_get_or_create_client)

    manager = MCPClientManager([])
    caplog.set_level(logging.WARNING)
    result = await manager.get_all_tools()

    assert result == []
    assert "No tools available from MCP servers" in caplog.text


@pytest.mark.asyncio
async def test_get_all_tools_client_raises_round_075(monkeypatch, caplog):
    """If client.get_tools raises an exception, get_all_tools should catch it, log an error, and return []."""

    class FakeClientBroken:
        async def get_tools(self):
            raise Exception("boom")

    async def fake_get_or_create_client(self):
        return FakeClientBroken()

    monkeypatch.setattr(MCPClientManager, "get_or_create_client", fake_get_or_create_client)

    manager = MCPClientManager([])
    caplog.set_level(logging.ERROR)
    result = await manager.get_all_tools()

    assert result == []
    assert "Error getting MCP tools: boom" in caplog.text
