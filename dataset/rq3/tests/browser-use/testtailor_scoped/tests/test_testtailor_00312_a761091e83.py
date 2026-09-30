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
        """Verify ContentPartTextParam.__repr__ uses _truncate correctly for short and long text."""
        # short text: should not be truncated
        short = "Hello short text"
        short_param = ContentPartTextParam(text=short)
        self.assertEqual(repr(short_param), f"ContentPartTextParam(text={short})")

        # long text: should be truncated to 50 chars total with ellipsis
        long_text = "https://example.com/" + ("x" * 100)
        long_param = ContentPartTextParam(text=long_text)
        expected_truncated = long_text[:47] + "..."
        self.assertEqual(repr(long_param), f"ContentPartTextParam(text={expected_truncated})")
