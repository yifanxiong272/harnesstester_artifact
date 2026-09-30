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
        """Ensure _get_mcp_configs returns [] when researcher is missing."""
        # Create an instance without calling __init__ to avoid _get_config raising
        retriever = object.__new__(MCPRetriever)
        # Ensure researcher attribute is missing / None to hit the final 'return []' branch
        retriever.researcher = None

        result = MCPRetriever._get_mcp_configs(retriever)
        self.assertEqual(result, [])
