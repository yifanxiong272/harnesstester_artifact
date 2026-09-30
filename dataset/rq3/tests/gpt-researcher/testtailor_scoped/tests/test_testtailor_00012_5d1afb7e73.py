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
        """Verify MCPClientManager initializer sets defaults for mcp_configs,
        _client and _client_lock."""
        # Case 1: mcp_configs is None -> should default to empty list
        mgr_none = MCPClientManager(None)
        self.assertEqual(mgr_none.mcp_configs, [])
        self.assertIsNone(mgr_none._client)
        # _client_lock should be an asyncio Lock-like object
        self.assertTrue(hasattr(mgr_none._client_lock, "acquire"))
        self.assertTrue(hasattr(mgr_none._client_lock, "release"))

        # Case 2: provided mcp_configs preserved as-is
        sample_configs = [{"name": "mcp1", "connection_url": "http://example"}]
        mgr_provided = MCPClientManager(sample_configs)
        self.assertIs(mgr_provided.mcp_configs, sample_configs)
        self.assertIsNone(mgr_provided._client)
        self.assertTrue(hasattr(mgr_provided._client_lock, "acquire"))
        self.assertTrue(hasattr(mgr_provided._client_lock, "release"))
