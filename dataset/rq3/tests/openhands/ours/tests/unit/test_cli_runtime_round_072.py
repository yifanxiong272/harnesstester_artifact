import asyncio
import sys
import types
from types import SimpleNamespace, ModuleType
import pytest

from openhands.runtime.impl.cli import cli_runtime

# Lightweight replacement classes to assert returned observations deterministically
class DummyErrorObservation:
    def __init__(self, message):
        self.message = message
    def __repr__(self):
        return f"DummyErrorObservation({self.message!r})"

@pytest.mark.asyncio
async def test_mcp_disabled_on_windows_round_072(monkeypatch):
    """When sys.platform == 'win32', the method should short-circuit with an ErrorObservation
    and log an info message."""
    # Force Windows platform
    monkeypatch.setattr(sys, "platform", "win32", raising=False)

    logs = []

    # Minimal fake self providing the attributes/methods used by the method
    fake_self = SimpleNamespace()
    fake_self.sid = "SOME_SID"
    fake_self.get_mcp_config = lambda: None  # not reached on Windows
    def log_fn(level, msg):
        logs.append((level, msg))
    fake_self.log = log_fn

    # Patch ErrorObservation symbol in module to deterministic dummy
    monkeypatch.setattr(cli_runtime, "ErrorObservation", DummyErrorObservation, raising=False)

    # Minimal action object with a name property
    action = SimpleNamespace(name="test_action", arguments={})

    result = await cli_runtime.CLIRuntime.call_tool_mcp(fake_self, action)

    assert isinstance(result, DummyErrorObservation)
    assert "MCP functionality is not available on Windows" in result.message
    assert ("info", "MCP functionality is disabled on Windows") in logs


@pytest.mark.asyncio
async def test_no_mcp_servers_configured_round_072(monkeypatch):
    """When MCP config has no servers, method logs a warning and returns ErrorObservation."""
    monkeypatch.setattr(sys, "platform", "linux", raising=False)

    logs = []
    fake_self = SimpleNamespace()
    fake_self.sid = "SID"
    def log_fn(level, msg):
        logs.append((level, msg))
    fake_self.log = log_fn

    # MCP config with all empty server lists
    class MCPConfig:
        def __init__(self):
            self.sse_servers = []
            self.shttp_servers = []
            self.stdio_servers = []
    fake_self.get_mcp_config = lambda: MCPConfig()

    # Provide a stub openhands.mcp.utils module so imports inside function succeed
    mcp_mod = ModuleType("openhands.mcp.utils")
    async def create_mcp_clients(*args, **kwargs):
        # Not reached because config has no servers, but keep signature
        return None
    async def call_tool_mcp(*args, **kwargs):
        return SimpleNamespace(ok=True)
    mcp_mod.create_mcp_clients = create_mcp_clients
    mcp_mod.call_tool_mcp = call_tool_mcp
    monkeypatch.setitem(sys.modules, "openhands.mcp.utils", mcp_mod)

    monkeypatch.setattr(cli_runtime, "ErrorObservation", DummyErrorObservation, raising=False)

    action = SimpleNamespace(name="test_action", arguments={})
    result = await cli_runtime.CLIRuntime.call_tool_mcp(fake_self, action)

    assert isinstance(result, DummyErrorObservation)
    assert "No MCP servers configured" in result.message
    assert ("warning", "No MCP servers configured") in logs


@pytest.mark.asyncio
async def test_no_mcp_clients_created_round_072(monkeypatch):
    """If create_mcp_clients returns falsy, method should warn and return ErrorObservation."""
    monkeypatch.setattr(sys, "platform", "linux", raising=False)

    logs = []
    fake_self = SimpleNamespace()
    fake_self.sid = "SID"
    def log_fn(level, msg):
        logs.append((level, msg))
    fake_self.log = log_fn

    class MCPConfig:
        def __init__(self):
            # Provide at least one server to bypass the 'no servers' branch
            self.sse_servers = ["sse:1"]
            self.shttp_servers = []
            self.stdio_servers = []
    fake_self.get_mcp_config = lambda: MCPConfig()

    # Provide module where create_mcp_clients returns falsy
    mcp_mod = ModuleType("openhands.mcp.utils")
    async def create_mcp_clients(sse, shttp, sid, stdio):
        return []  # falsy
    async def call_tool_mcp(clients, action):
        return SimpleNamespace(ok=True)
    mcp_mod.create_mcp_clients = create_mcp_clients
    mcp_mod.call_tool_mcp = call_tool_mcp
    monkeypatch.setitem(sys.modules, "openhands.mcp.utils", mcp_mod)

    monkeypatch.setattr(cli_runtime, "ErrorObservation", DummyErrorObservation, raising=False)

    action = SimpleNamespace(name="mcp_act", arguments={})
    result = await cli_runtime.CLIRuntime.call_tool_mcp(fake_self, action)

    assert isinstance(result, DummyErrorObservation)
    assert "No MCP clients could be created" in result.message
    assert ("warning", "No MCP clients could be created") in logs


@pytest.mark.asyncio
async def test_successful_mcp_call_round_072(monkeypatch):
    """When clients are created and call_tool_mcp returns an observation, it should be returned intact and debug logged."""
    monkeypatch.setattr(sys, "platform", "linux", raising=False)

    logs = []
    fake_self = SimpleNamespace()
    fake_self.sid = "SID"
    def log_fn(level, msg):
        logs.append((level, msg))
    fake_self.log = log_fn

    class MCPConfig:
        def __init__(self):
            self.sse_servers = ["sse:1"]
            self.shttp_servers = ["http:1"]
            self.stdio_servers = []
    fake_self.get_mcp_config = lambda: MCPConfig()

    # Provide module where clients creation succeeds and handler returns a sentinel
    sentinel = SimpleNamespace(result="ok")
    mcp_mod = ModuleType("openhands.mcp.utils")
    async def create_mcp_clients(sse, shttp, sid, stdio):
        # return a truthy clients collection
        return ["clientA"]
    async def call_tool_mcp(clients, action):
        return sentinel
    mcp_mod.create_mcp_clients = create_mcp_clients
    mcp_mod.call_tool_mcp = call_tool_mcp
    monkeypatch.setitem(sys.modules, "openhands.mcp.utils", mcp_mod)

    # Replace ErrorObservation with deterministic class to ensure we would not confuse types
    monkeypatch.setattr(cli_runtime, "ErrorObservation", DummyErrorObservation, raising=False)

    action = SimpleNamespace(name="good_action", arguments={"x": 1})
    result = await cli_runtime.CLIRuntime.call_tool_mcp(fake_self, action)

    # Should return the sentinel directly
    assert result is sentinel
    # Ensure debug log for successful execution was emitted
    assert any(item[0] == "debug" and "executed successfully" in item[1] for item in logs)


@pytest.mark.asyncio
async def test_call_tool_mcp_raises_round_072(monkeypatch):
    """If call_tool_mcp handler raises, the method should catch, log an error and return ErrorObservation with message including exception text."""
    monkeypatch.setattr(sys, "platform", "linux", raising=False)

    logs = []
    fake_self = SimpleNamespace()
    fake_self.sid = "SID"
    def log_fn(level, msg):
        logs.append((level, msg))
    fake_self.log = log_fn

    class MCPConfig:
        def __init__(self):
            self.sse_servers = ["sse:1"]
            self.shttp_servers = []
            self.stdio_servers = []
    fake_self.get_mcp_config = lambda: MCPConfig()

    mcp_mod = ModuleType("openhands.mcp.utils")
    async def create_mcp_clients(sse, shttp, sid, stdio):
        return ["clientX"]
    async def call_tool_mcp(clients, action):
        raise RuntimeError("boom")
    mcp_mod.create_mcp_clients = create_mcp_clients
    mcp_mod.call_tool_mcp = call_tool_mcp
    monkeypatch.setitem(sys.modules, "openhands.mcp.utils", mcp_mod)

    monkeypatch.setattr(cli_runtime, "ErrorObservation", DummyErrorObservation, raising=False)

    action = SimpleNamespace(name="test", arguments={})
    result = await cli_runtime.CLIRuntime.call_tool_mcp(fake_self, action)

    assert isinstance(result, DummyErrorObservation)
    assert "Error executing MCP tool test: boom" in result.message
    assert any(item[0] == "error" and "Error executing MCP tool" in item[1] for item in logs)
