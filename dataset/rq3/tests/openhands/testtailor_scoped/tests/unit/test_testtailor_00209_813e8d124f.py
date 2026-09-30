import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.mcp.client')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """Ensure _initialize_and_list_tools creates MCPClientTool objects, populates tools and tool_map."""
        async def run():
            # Create MCPClient instance under test
            mcp_client = MCPClient()

            # Dummy tool objects returned by the client.list_tools()
            class DummyTool:
                def __init__(self, name, description, inputSchema):
                    self.name = name
                    self.description = description
                    self.inputSchema = inputSchema

            # Dummy client that acts as an async context manager and provides list_tools()
            class DummyClient:
                def __init__(self, tools):
                    self._tools = tools

                async def __aenter__(self):
                    return self

                async def __aexit__(self, exc_type, exc, tb):
                    # Return False to propagate exceptions if any (mirrors normal context behavior)
                    return False

                async def list_tools(self):
                    # Simulate an async call to list tools on the server
                    return self._tools

            # Prepare dummy tools and attach dummy client to MCPClient
            dummy_tools = [
                DummyTool("tool_one", "First tool", {"type": "object"}),
                DummyTool("tool_two", "Second tool", {"type": "object"}),
            ]
            dummy_client = DummyClient(dummy_tools)
            mcp_client.client = dummy_client

            # Call the method under test
            await mcp_client._initialize_and_list_tools()

            # Assertions: tools list populated, tool_map contains entries, objects are MCPClientTool
            self.assertEqual(len(mcp_client.tools), 2)
            self.assertIn("tool_one", mcp_client.tool_map)
            self.assertIn("tool_two", mcp_client.tool_map)
            # tool_map values should be the same objects as in tools list (matching by name)
            tool_names = [t.name for t in mcp_client.tools]
            self.assertCountEqual(tool_names, ["tool_one", "tool_two"])
            # Each entry in tools is an MCPClientTool and has expected description
            found = {t.name: t for t in mcp_client.tools}
            self.assertIsInstance(found["tool_one"], MCPClientTool)
            self.assertEqual(found["tool_one"].description, "First tool")
            self.assertIsInstance(found["tool_two"], MCPClientTool)
            self.assertEqual(found["tool_two"].description, "Second tool")
            # tool_map values reference the same MCPClientTool instances as in tools
            self.assertIs(mcp_client.tool_map["tool_one"], found["tool_one"])
            self.assertIs(mcp_client.tool_map["tool_two"], found["tool_two"])

        # Use a fresh event loop to avoid issues if the test runner already has a running loop.
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run())
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            loop.close()
            asyncio.set_event_loop(None)
