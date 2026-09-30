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
        """Truncate returns an ellipsized string of the requested length when input is longer than max_length."""
        # longer input than max_length -> should hit the truncation branch
        long_text = "The quick brown fox jumps over the lazy dog and then keeps going"
        truncated = _truncate(long_text, max_length=20)
        # ends with ellipsis and total length equals max_length
        self.assertTrue(truncated.endswith("..."))
        self.assertEqual(len(truncated), 20)
        # prefix preserved up to max_length - 3
        self.assertEqual(truncated, long_text[: 20 - 3] + "...")

        # another simple numeric example
        result = _truncate("abcdefghij", max_length=5)  # expects 'ab...'
        self.assertEqual(result, "ab...")
        self.assertEqual(len(result), 5)
