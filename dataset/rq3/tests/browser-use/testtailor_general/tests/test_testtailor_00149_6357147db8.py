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
        """Ensure _laminar_preview truncates long text and non-str serialized values correctly."""
        # Direct string longer than limit should be truncated with the expected suffix
        long_text = "x" * 100
        result = _laminar_preview(long_text, limit=50)
        expected = long_text[:50] + f'...[truncated {len(long_text) - 50} chars]'
        self.assertEqual(result, expected)

        # Non-str value is serialized via json.dumps and then truncated
        value = {"key": "y" * 120}
        serialized = json.dumps(value, default=str)
        result2 = _laminar_preview(value, limit=40)
        expected2 = serialized[:40] + f'...[truncated {len(serialized) - 40} chars]'
        self.assertEqual(result2, expected2)

        # When text length is <= limit, the original text should be returned unchanged
        short_text = "short"
        self.assertEqual(_laminar_preview(short_text, limit=10), short_text)
