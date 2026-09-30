import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.beta.service')
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
        """Ensure _laminar_preview truncates long strings and reports truncated length."""
        # create a string longer than the default limit to force truncation branch
        long_text = "x" * 2500
        # call the function under test with an explicit smaller limit
        preview = _laminar_preview(long_text, limit=2000)
        expected = long_text[:2000] + f'...[truncated {len(long_text) - 2000} chars]'
        self.assertEqual(preview, expected)
