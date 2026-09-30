import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.mcp.client')
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
        """If already connected, connect() should return immediately and not start background tasks or change state."""
        client = MCPClient(server_name="test_server", command="echo", args=["hello"])

        # Simulate already connected
        client._connected = True

        # Replace telemetry with a dummy that will mark if called (should not be called on early return)
        telemetry_called = {"capture": False, "flush": False}

        class DummyTelemetry:
            def capture(self, *args, **kwargs):
                telemetry_called["capture"] = True

            def flush(self, *args, **kwargs):
                telemetry_called["flush"] = True

        client._telemetry = DummyTelemetry()

        # Put an existing tool entry to ensure connect does not mutate tools
        existing_tool = object()
        client._tools = {"existing": existing_tool}
        client._stdio_task = None

        # Call connect (async); should return immediately
        asyncio.run(client.connect())

        # Ensure no changes happened
        self.assertTrue(client._connected)
        self.assertIs(client._tools.get("existing"), existing_tool)
        self.assertIsNone(client._stdio_task)

        # Telemetry should not have been invoked on the early return path
        self.assertFalse(telemetry_called["capture"])
        self.assertFalse(telemetry_called["flush"])
