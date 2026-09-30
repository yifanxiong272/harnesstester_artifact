import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.mcp.client')
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
        """Ensure a connection_url starting with wss:// yields websocket transport and URL set."""
        # Prepare a config that should trigger websocket transport detection
        config = {
            "name": "remote_ws",
            "connection_url": "wss://example.com/mcp"
        }
        manager = MCPClientManager([config])

        # Execute the conversion
        server_configs = manager.convert_configs_to_langchain_format()

        # Assertions: server name exists and transport + url are correctly set
        self.assertIn("remote_ws", server_configs)
        server_cfg = server_configs["remote_ws"]
        self.assertEqual(server_cfg.get("transport"), "websocket")
        self.assertEqual(server_cfg.get("url"), "wss://example.com/mcp")
