import sys
import types
import asyncio
from types import SimpleNamespace
import pytest

from openhands.events.observation import ErrorObservation
from openhands.runtime.impl.cli import cli_runtime

# We'll call the unbound method CLIRuntime.call_tool_mcp with a lightweight fake
# `self` object providing only the attributes the method uses: sid, get_mcp_config, log.

class DummySelf:
    def __init__(self, sid, mcp_config):
        self.sid = sid
        self._mcp_config = mcp_config
        self.logs = []

    def get_mcp_config(self):
        return self._mcp_config

    def log(self, level, message):
        # Preserve payload shape (level, message)
        self.logs.append((level, message))


def _install_mcp_utils_module(create_mcp_clients_fn, call_tool_mcp_fn):
    """Create a fake openhands.mcp.utils module in sys.modules with the
    provided callables. These must be regular callables; the function under
    test awaits them, so make them async where needed in tests."""
    mod = types.ModuleType("openhands.mcp.utils")
    mod.create_mcp_clients = create_mcp_clients_fn
    mod.call_tool_mcp = call_tool_mcp_fn
    sys.modules["openhands.mcp.utils"] = mod


@pytest.mark.asyncio
async def test_win32_branch_round_072(monkeypatch):
    # Simulate running on Windows -> immediate return with ErrorObservation
    monkeypatch.setattr(sys, "platform", "win32")

    # Minimal dummy self and action
    cfg = SimpleNamespace(sse_servers=[], shttp_servers=[], stdio_servers=[])
    dummy = DummySelf(sid="S1", mcp_config=cfg)
    action = SimpleNamespace(name="act", arguments={})

    # Call the unbound method directly with our dummy self
    result = await cli_runtime.CLIRuntime.call_tool_mcp(dummy, action)

    # Assert an ErrorObservation was returned and that an info-level log was produced
    assert isinstance(result, ErrorObservation)
    assert any(lvl == "info" and "MCP functionality is disabled on Windows" in msg for lvl, msg in dummy.logs)


@pytest.mark.asyncio
async def test_no_servers_configured_round_072(monkeypatch):
    # Non-Windows platform
    monkeypatch.setattr(sys, "platform", "linux")

    # get_mcp_config returns empty server lists -> should log warning and return ErrorObservation
    cfg = SimpleNamespace(sse_servers=[], shttp_servers=[], stdio_servers=[])
    dummy = DummySelf(sid="S2", mcp_config=cfg)
    action = SimpleNamespace(name="no_servers", arguments={})

    # Ensure the internal import succeeds with dummy implementations that should not be reached
    async def fake_create_mcp_clients(*args, **kwargs):
        return ["should-not-be-used"]

    async def fake_call_tool_mcp(clients, action):
        return SimpleNamespace(ok=True)

    _install_mcp_utils_module(fake_create_mcp_clients, fake_call_tool_mcp)

    result = await cli_runtime.CLIRuntime.call_tool_mcp(dummy, action)

    assert isinstance(result, ErrorObservation)
    # The code logs a specific warning message for no servers configured
    assert any(lvl == "warning" and "No MCP servers configured" in msg for lvl, msg in dummy.logs)


@pytest.mark.asyncio
async def test_no_clients_created_round_072(monkeypatch):
    # Non-Windows platform
    monkeypatch.setattr(sys, "platform", "linux")

    # Provide one server so the code attempts to create clients
    cfg = SimpleNamespace(sse_servers=["sse1"], shttp_servers=[], stdio_servers=[])
    dummy = DummySelf(sid="S3", mcp_config=cfg)
    action = SimpleNamespace(name="no_clients", arguments={})

    # create_mcp_clients returns an empty/falsy value -> triggers no-clients branch
    async def fake_create_mcp_clients(sse, shttp, sid, stdio):
        # Ensure we capture the incoming arguments shapes
        assert sse == cfg.sse_servers
        assert shttp == cfg.shttp_servers
        assert sid == dummy.sid
        assert stdio == cfg.stdio_servers
        return []

    async def fake_call_tool_mcp(clients, action):
        return SimpleNamespace(ok=True)

    _install_mcp_utils_module(fake_create_mcp_clients, fake_call_tool_mcp)

    result = await cli_runtime.CLIRuntime.call_tool_mcp(dummy, action)

    assert isinstance(result, ErrorObservation)
    # The code logs a specific warning message for no clients created
    assert any(lvl == "warning" and "No MCP clients could be created" in msg for lvl, msg in dummy.logs)


@pytest.mark.asyncio
async def test_exception_path_round_072(monkeypatch):
    # Non-Windows platform but create_mcp_clients raises -> except block
    monkeypatch.setattr(sys, "platform", "linux")

    cfg = SimpleNamespace(sse_servers=["sse1"], shttp_servers=[], stdio_servers=[])
    dummy = DummySelf(sid="S4", mcp_config=cfg)
    action = SimpleNamespace(name="explosion", arguments={})

    async def raising_create_mcp_clients(*args, **kwargs):
        raise RuntimeError("boom-from-create")

    async def fake_call_tool_mcp(clients, action):
        return SimpleNamespace(ok=True)

    _install_mcp_utils_module(raising_create_mcp_clients, fake_call_tool_mcp)

    result = await cli_runtime.CLIRuntime.call_tool_mcp(dummy, action)

    # An ErrorObservation should be returned and an error-level log should include the action name
    assert isinstance(result, ErrorObservation)
    assert any(lvl == "error" and f"Error executing MCP tool {action.name}" in msg for lvl, msg in dummy.logs)
