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
        """Test conversion when config has no name and provides an HTTPS connection_url."""
        # Config without explicit name should get default "mcp_server_1"
        cfg = {
            "connection_url": "https://example.com/api",
            "connection_token": "secret-token-123"
        }
        mgr = MCPClientManager([cfg])
        server_configs = mgr.convert_configs_to_langchain_format()

        # Verify default server name created and configuration populated
        self.assertIn("mcp_server_1", server_configs)
        sc = server_configs["mcp_server_1"]

        # HTTPS URL should set transport to streamable_http and include the URL
        self.assertEqual(sc.get("transport"), "streamable_http")
        self.assertEqual(sc.get("url"), "https://example.com/api")

        # Token should be forwarded
        self.assertEqual(sc.get("token"), "secret-token-123")
