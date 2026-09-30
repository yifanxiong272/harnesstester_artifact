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
        """Verify MCPClient.__init__ sets defaults and stores provided values."""
        # Create client with default args/env
        client = MCPClient("test_server", "python")

        # Basic properties
        self.assertEqual(client.server_name, "test_server")
        self.assertEqual(client.command, "python")

        # Defaults
        self.assertEqual(client.args, [])
        self.assertIsNone(client.env)

        # Connection/session related defaults
        self.assertIsNone(client.session)
        self.assertIsNone(client._stdio_task)
        self.assertIsNone(client._read_stream)
        self.assertIsNone(client._write_stream)

        # Tool/registration state defaults
        self.assertEqual(client._tools, {})
        self.assertEqual(client._registered_actions, set())
        self.assertFalse(client._connected)

        # Disconnect event should exist and support expected methods
        self.assertTrue(hasattr(client._disconnect_event, "is_set"))
        self.assertTrue(callable(getattr(client._disconnect_event, "is_set")))
        self.assertTrue(hasattr(client._disconnect_event, "set"))
        self.assertTrue(callable(getattr(client._disconnect_event, "set")))

        # Telemetry object should expose expected methods
        self.assertTrue(hasattr(client._telemetry, "capture"))
        self.assertTrue(callable(getattr(client._telemetry, "capture")))
        self.assertTrue(hasattr(client._telemetry, "flush"))
        self.assertTrue(callable(getattr(client._telemetry, "flush")))

        # Also verify that provided args/env are stored if passed
        custom_args = ["@playwright/mcp@latest"]
        custom_env = {"FOO": "BAR"}
        client2 = MCPClient("other_server", "npx", args=custom_args, env=custom_env)
        self.assertEqual(client2.server_name, "other_server")
        self.assertEqual(client2.command, "npx")
        self.assertEqual(client2.args, custom_args)
        self.assertEqual(client2.env, custom_env)
