# file: browser_use/mcp/client.py:248-409
# asked: {"lines": [257, 259, 261, 262, 264, 266, 269, 270, 273, 274, 275, 277, 280, 281, 282, 284, 287, 289, 290, 292, 295, 298, 301, 307, 309, 311, 312, 315, 317, 319, 320, 322, 324, 327, 329, 330, 331, 332, 335, 336, 337, 338, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 356, 358, 359, 361, 363, 364, 366, 368, 371, 373, 374, 375, 376, 379, 380, 381, 382, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 400, 401, 404, 407, 409], "branches": [[259, 261], [259, 287], [264, 266], [264, 287], [269, 270], [269, 273], [274, 275], [274, 277], [281, 282], [281, 284], [287, 289], [287, 295], [307, 309], [307, 356], [311, 312], [311, 315], [358, 359], [358, 361]]}
# gained: {"lines": [257, 259, 261, 262, 264, 266, 269, 270, 273, 274, 275, 280, 281, 282, 284, 287, 289, 290, 292, 295, 298, 301, 307, 309, 311, 312, 315, 317, 319, 320, 322, 324, 327, 329, 330, 331, 332, 335, 336, 337, 338, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 356, 358, 359, 361, 363, 364, 366, 368, 371, 373, 374, 375, 376, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 400, 401, 404, 407, 409], "branches": [[259, 261], [259, 287], [264, 266], [264, 287], [269, 270], [269, 273], [274, 275], [281, 282], [287, 289], [287, 295], [307, 309], [307, 356], [311, 312], [311, 315], [358, 359], [358, 361]]}

import asyncio
from types import SimpleNamespace
import pytest

from browser_use.agent.views import ActionResult
from browser_use.mcp.client import MCPClient
from browser_use.telemetry import MCPClientTelemetryEvent


class FakeRegistry:
    def __init__(self):
        self.registered = []

    def action(self, description=None, param_model=None, domains=None):
        # Return a decorator that saves metadata and the function
        def decorator(func):
            self.registered.append({
                "func": func,
                "description": description,
                "param_model": param_model,
                "domains": domains,
            })
            return func
        return decorator


class FakeTelemetry:
    def __init__(self):
        self.captured = []

    def capture(self, ev: MCPClientTelemetryEvent):
        self.captured.append(ev)


class FakeSessionSuccess:
    def __init__(self, result):
        self._result = result
        self.calls = []

    async def call_tool(self, name, params):
        self.calls.append((name, params))
        return self._result


class FakeSessionError:
    def __init__(self, exc):
        self.exc = exc
        self.calls = []

    async def call_tool(self, name, params):
        self.calls.append((name, params))
        raise self.exc


@pytest.mark.asyncio
async def test_register_tool_with_params_success_and_error(monkeypatch):
    """
    Test registering a tool that has an inputSchema (param_model case).
    Covers:
    - model creation from inputSchema
    - wrapper behavior when not connected
    - wrapper behavior on success (session.call_tool returns value)
    - wrapper behavior on exception
    - telemetry capture in finally block
    - registry decorator registration and metadata
    """
    registry = FakeRegistry()
    telemetry = FakeTelemetry()

    client = MCPClient("testserver", "testcmd")
    client._tools = [1, 2, 3]
    client._telemetry = telemetry

    # Make json schema -> python type mapping predictable: return str for any field
    monkeypatch.setattr(client, "_json_schema_to_python_type", lambda schema, name: str)
    monkeypatch.setattr(client, "_format_mcp_result", lambda r: f"formatted:{r}")

    # Tool with inputSchema: one required field "a" and one optional "b" with default
    tool = SimpleNamespace(
        name="mcp_tool_x",
        inputSchema={
            "properties": {
                "a": {"type": "string", "description": "A required"},
                "b": {"type": "string", "default": "def", "description": "Optional b"},
            },
            "required": ["a"],
        },
        description="A test MCP tool",
    )

    # Case: not connected -> wrapper should return ActionResult with error and not call session
    client.session = None
    client._connected = False

    # Register
    client._register_tool_as_action(registry, "action_x", tool)

    # Ensure registry recorded registration
    assert len(registry.registered) == 1
    meta = registry.registered[0]
    assert meta["description"] == "A test MCP tool"
    # param_model should be a pydantic model class
    param_model = meta["param_model"]
    assert hasattr(param_model, "model_fields")

    # Call the registered function (should be the wrapper)
    wrapper = meta["func"]

    # Ensure metadata name and qualname set on function
    assert wrapper.__name__ == "action_x"
    assert wrapper.__qualname__ == f"mcp.{client.server_name}.action_x"

    # When not connected return error
    res = await wrapper(param_model(a="val"))
    assert isinstance(res, ActionResult)
    assert res.success is False
    assert "not connected" in (res.error or "").lower()

    # Now test success path: set connected and session that returns a value
    session = FakeSessionSuccess({"result": "ok"})
    client.session = session
    client._connected = True

    # Call wrapper with required param; optional 'b' should be omitted and not sent
    params_instance = param_model(a="aval")
    res2 = await wrapper(params_instance)
    assert isinstance(res2, ActionResult)
    assert res2.error is None
    assert "formatted" in (res2.extracted_content or "")

    # Telemetry should have been captured at least once (from success path)
    assert any(isinstance(ev, MCPClientTelemetryEvent) for ev in telemetry.captured)
    last_event = telemetry.captured[-1]
    assert last_event.server_name == client.server_name
    assert last_event.action == "tool_call"
    assert last_event.tool_name == tool.name

    # Now test exception path: session that raises
    telemetry.captured.clear()
    session_err = FakeSessionError(RuntimeError("boom"))
    client.session = session_err
    client._connected = True

    res3 = await wrapper(param_model(a="x"))
    assert isinstance(res3, ActionResult)
    assert res3.success is False
    assert "failed" in (res3.error or "").lower()
    # Telemetry should capture with error_message set
    assert telemetry.captured, "telemetry should have been captured on exception"
    assert any(getattr(ev, "error_message", None) is not None for ev in telemetry.captured)


@pytest.mark.asyncio
async def test_register_tool_no_params_and_not_connected_and_success(monkeypatch):
    """
    Test registering a tool with no parameters (param_model == None).
    Covers:
    - wrapper with no params
    - not connected path
    - success path where call_tool is called with empty dict
    - telemetry captured
    - registry metadata description fallback (when description missing)
    """
    registry = FakeRegistry()
    telemetry = FakeTelemetry()

    client = MCPClient("srv", "cmd")
    client._tools = []
    client._telemetry = telemetry

    # Tool without inputSchema (or empty)
    tool = SimpleNamespace(
        name="browser_do_something",  # startswith browser_ -> is_browser_tool True path possibility
        inputSchema=None,
        description=None,  # force fallback description
    )

    # monkeypatch format function
    monkeypatch.setattr(client, "_format_mcp_result", lambda r: f"f:{r}")

    client.session = None
    client._connected = False

    client._register_tool_as_action(registry, "no_params_action", tool)

    assert len(registry.registered) == 1
    meta = registry.registered[0]
    assert meta["param_model"] is None
    assert meta["description"] == f"MCP tool from {client.server_name}: {tool.name}"

    wrapper = meta["func"]
    # not connected path should return not connected error
    res = await wrapper()
    assert isinstance(res, ActionResult)
    assert res.success is False
    assert "not connected" in (res.error or "").lower()

    # success path: set session that returns value
    session = FakeSessionSuccess({"ok": True})
    client.session = session
    client._connected = True

    res2 = await wrapper()
    assert isinstance(res2, ActionResult)
    assert res2.error is None
    assert "f:" in (res2.extracted_content or "")

    # ensure call_tool was called with empty params
    assert session.calls and session.calls[-1] == (tool.name, {})

    # telemetry captured and has expected fields
    assert telemetry.captured
    ev = telemetry.captured[-1]
    assert ev.server_name == client.server_name
    assert ev.action == "tool_call"
    assert ev.tool_name == tool.name
