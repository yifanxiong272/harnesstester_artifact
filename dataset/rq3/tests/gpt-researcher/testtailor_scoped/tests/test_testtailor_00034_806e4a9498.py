import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.chat.chat')
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
        """Verify get_tools returns the expected function tool definition for quick_search."""
        tools = get_tools()

        # Basic structure checks
        self.assertIsInstance(tools, list)
        self.assertEqual(len(tools), 1)

        tool = tools[0]
        self.assertIsInstance(tool, dict)
        self.assertEqual(tool.get("type"), "function")

        # Function object checks
        function_def = tool.get("function")
        self.assertIsInstance(function_def, dict)
        self.assertEqual(function_def.get("name"), "quick_search")
        self.assertEqual(
            function_def.get("description"),
            "Search for current events or online information when you need new knowledge that doesn't exist in the current context"
        )

        # Parameters schema checks
        params = function_def.get("parameters")
        self.assertIsInstance(params, dict)
        self.assertEqual(params.get("type"), "object")

        properties = params.get("properties")
        self.assertIsInstance(properties, dict)
        self.assertIn("query", properties)

        query_prop = properties["query"]
        self.assertIsInstance(query_prop, dict)
        self.assertEqual(query_prop.get("type"), "string")
        self.assertEqual(query_prop.get("description"), "The search query")

        required = params.get("required")
        self.assertIsInstance(required, list)
        self.assertEqual(required, ["query"])
