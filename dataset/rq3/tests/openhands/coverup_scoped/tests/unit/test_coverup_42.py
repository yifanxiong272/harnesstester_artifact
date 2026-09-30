# file: openhands/runtime/impl/cli/cli_runtime.py:694-757
# asked: {"lines": [704, 705, 706, 709, 710, 712, 714, 717, 718, 719, 721, 722, 724, 725, 726, 727, 728, 732, 733, 734, 735, 736, 739, 740, 741, 742, 746, 747, 748, 750, 751, 752, 754, 755, 756, 757], "branches": [[704, 705], [704, 709], [716, 721], [716, 724], [739, 740], [739, 746]]}
# gained: {"lines": [704, 705, 706, 709, 710, 712, 714, 717, 718, 719, 721, 722, 724, 725, 726, 727, 728, 732, 733, 734, 735, 736, 739, 740, 741, 742, 746, 747, 748, 750, 751, 752, 754, 755, 756, 757], "branches": [[704, 705], [704, 709], [716, 721], [716, 724], [739, 740], [739, 746]]}

import sys
import types
from types import SimpleNamespace

import pytest

from openhands.events.observation import ErrorObservation
from openhands.runtime.impl.cli.cli_runtime import CLIRuntime


@pytest.mark.asyncio
async def test_call_tool_mcp_on_windows_returns_error(monkeypatch):
    # Force platform to windows
    monkeypatch.setattr(sys, "platform", "win32")
    # Create a minimal runtime instance without running __init__
    runtime = CLIRuntime.__new__(CLIRuntime)
    logs = []

    # simple log collector
    runtime.log = lambda level, msg: logs.append((level, msg))
    # call with a dummy action
    action = SimpleNamespace(name="mcp_tool", arguments={})
    result = await CLIRuntime.call_tool_mcp(runtime, action)

    assert isinstance(result, ErrorObservation)
    # Error message available via .message property
    assert "MCP functionality is not available on Windows" in result.message
    assert ("info", "MCP functionality is disabled on Windows") in logs


@pytest.mark.asyncio
async def test_call_tool_mcp_no_servers_configured_returns_error(monkeypatch):
    # Ensure non-windows
    monkeypatch.setattr(sys, "platform", "linux")
    # Provide a dummy openhands.mcp.utils module to satisfy imports (not used in this branch)
    mcp_utils = types.ModuleType("openhands.mcp.utils")

    async def fake_create_mcp_clients(*args, **kwargs):
        return []
    async def fake_call_tool_mcp_handler(*args, **kwargs):
        return SimpleNamespace(ok=True)
    mcp_utils.create_mcp_clients = fake_create_mcp_clients
    mcp_utils.call_tool_mcp = fake_call_tool_mcp_handler
    monkeypatch.setitem(sys.modules, "openhands.mcp.utils", mcp_utils)

    runtime = CLIRuntime.__new__(CLIRuntime)
    logs = []
    runtime.log = lambda level, msg: logs.append((level, msg))

    # mcp_config with no servers
    mcp_config = SimpleNamespace(sse_servers=[], shttp_servers=[], stdio_servers=[])
    runtime.get_mcp_config = lambda: mcp_config
    runtime.sid = "sid"

    action = SimpleNamespace(name="mcp_tool", arguments={})
    result = await CLIRuntime.call_tool_mcp(runtime, action)

    assert isinstance(result, ErrorObservation)
    assert "No MCP servers configured" in result.message
    assert ("warning", "No MCP servers configured") in logs


@pytest.mark.asyncio
async def test_call_tool_mcp_no_clients_created_returns_error(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    # Create a fake mcp utils module where create_mcp_clients returns empty list
    mcp_utils = types.ModuleType("openhands.mcp.utils")

    async def create_mcp_clients(sse, shttp, sid, stdio):
        return []  # falsy -> triggers branch
    async def call_tool_mcp_handler(clients, action):
        return SimpleNamespace(ok=True)
    mcp_utils.create_mcp_clients = create_mcp_clients
    mcp_utils.call_tool_mcp = call_tool_mcp_handler
    monkeypatch.setitem(sys.modules, "openhands.mcp.utils", mcp_utils)

    runtime = CLIRuntime.__new__(CLIRuntime)
    logs = []
    runtime.log = lambda level, msg: logs.append((level, msg))

    # mcp_config with some servers so we proceed to client creation
    mcp_config = SimpleNamespace(sse_servers=["sse1"], shttp_servers=[], stdio_servers=[])
    runtime.get_mcp_config = lambda: mcp_config
    runtime.sid = "sid"

    action = SimpleNamespace(name="mcp_tool", arguments={})
    result = await CLIRuntime.call_tool_mcp(runtime, action)

    assert isinstance(result, ErrorObservation)
    assert "No MCP clients could be created" in result.message
    assert any("No MCP clients could be created" in m for _, m in logs)


@pytest.mark.asyncio
async def test_call_tool_mcp_success_calls_handler_and_returns_result(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    # Create fake mcp utils module where create_mcp_clients returns clients and handler returns an observation-like object
    mcp_utils = types.ModuleType("openhands.mcp.utils")

    async def create_mcp_clients(sse, shttp, sid, stdio):
        return ["client1"]
    async def call_tool_mcp_handler(clients, action):
        # Return a Sentinel observation object
        return SimpleNamespace(observation="OK", value=123)
    mcp_utils.create_mcp_clients = create_mcp_clients
    mcp_utils.call_tool_mcp = call_tool_mcp_handler
    monkeypatch.setitem(sys.modules, "openhands.mcp.utils", mcp_utils)

    runtime = CLIRuntime.__new__(CLIRuntime)
    logs = []
    runtime.log = lambda level, msg: logs.append((level, msg))

    mcp_config = SimpleNamespace(sse_servers=["sse1"], shttp_servers=["http1"], stdio_servers=["stdio1"])
    runtime.get_mcp_config = lambda: mcp_config
    runtime.sid = "sid"

    action = SimpleNamespace(name="mcp_tool", arguments={"x": 1})
    result = await CLIRuntime.call_tool_mcp(runtime, action)

    # Should return the sentinel object from handler
    assert not isinstance(result, ErrorObservation)
    assert getattr(result, "observation", None) == "OK"
    assert getattr(result, "value", None) == 123
    # verify logs contain debug lines about creating clients and executing tool
    assert any("Creating MCP clients" in m for _, m in logs)
    assert any("Executing MCP tool" in m for _, m in logs)
    assert any("executed successfully" in m for _, m in logs)


@pytest.mark.asyncio
async def test_call_tool_mcp_exception_returns_error_observation(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    # fake mcp utils where create_mcp_clients raises
    mcp_utils = types.ModuleType("openhands.mcp.utils")

    async def create_mcp_clients(sse, shttp, sid, stdio):
        raise RuntimeError("boom")
    mcp_utils.create_mcp_clients = create_mcp_clients
    # handler not reached but define anyway
    async def call_tool_mcp_handler(clients, action):
        return SimpleNamespace(observation="SHOULD_NOT", value=0)
    mcp_utils.call_tool_mcp = call_tool_mcp_handler
    monkeypatch.setitem(sys.modules, "openhands.mcp.utils", mcp_utils)

    runtime = CLIRuntime.__new__(CLIRuntime)
    logs = []
    runtime.log = lambda level, msg: logs.append((level, msg))

    mcp_config = SimpleNamespace(sse_servers=["sse1"], shttp_servers=[], stdio_servers=[])
    runtime.get_mcp_config = lambda: mcp_config
    runtime.sid = "sid"

    action = SimpleNamespace(name="mcp_tool", arguments={})
    result = await CLIRuntime.call_tool_mcp(runtime, action)

    assert isinstance(result, ErrorObservation)
    assert "Error executing MCP tool mcp_tool: boom" in result.message
    assert any("Error executing MCP tool mcp_tool" in m for _, m in logs)
