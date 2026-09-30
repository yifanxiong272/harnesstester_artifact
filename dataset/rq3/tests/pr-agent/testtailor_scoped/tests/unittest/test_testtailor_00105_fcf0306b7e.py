import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.tools.pr_add_docs')
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
        """Return value should be 'JSdocs' for JavaScript/TypeScript languages."""
        # JavaScript (mixed-case) should be normalized to 'javascript' and return "JSdocs"
        result_js = get_docs_for_language("JavaScript", style="any")
        self.assertEqual(result_js, "JSdocs")

        # TypeScript should also return "JSdocs"
        result_ts = get_docs_for_language("TypeScript", style="any")
        self.assertEqual(result_ts, "JSdocs")
