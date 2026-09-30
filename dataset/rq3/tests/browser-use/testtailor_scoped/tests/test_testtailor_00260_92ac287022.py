import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.messages')
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
        """Verify ContentPartTextParam.__str__ uses _truncate correctly for short, exact, and long texts."""
        # short text - should not be truncated
        short = ContentPartTextParam(text="Hello, world!")
        self.assertEqual(str(short), "Text: Hello, world!")

        # exact boundary (50 chars) - should not be truncated
        exact50_text = "x" * 50
        exact50 = ContentPartTextParam(text=exact50_text)
        self.assertEqual(str(exact50), f"Text: {exact50_text}")

        # long text - should be truncated to 47 chars + '...'
        long_text = "a" * 60
        long = ContentPartTextParam(text=long_text)
        expected_truncated = "a" * 47 + "..."
        self.assertEqual(str(long), f"Text: {expected_truncated}")
