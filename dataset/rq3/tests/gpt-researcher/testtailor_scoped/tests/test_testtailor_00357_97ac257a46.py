import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.mcp.retriever')
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
        """MCPRetriever should raise ValueError when researcher or researcher.cfg is missing."""
        # Case 1: researcher is None -> should raise ValueError from _get_config
        with self.assertRaisesRegex(ValueError, "MCPRetriever requires a researcher instance with cfg attribute"):
            MCPRetriever("test query", researcher=None)

        # Case 2: researcher provided but missing cfg attribute -> should also raise ValueError
        class DummyResearcher:
            pass

        dummy = DummyResearcher()
        dummy.mcp_configs = [{"url": "http://example.com"}]  # has mcp_configs but no cfg
        with self.assertRaisesRegex(ValueError, "MCPRetriever requires a researcher instance with cfg attribute"):
            MCPRetriever("another query", researcher=dummy)
