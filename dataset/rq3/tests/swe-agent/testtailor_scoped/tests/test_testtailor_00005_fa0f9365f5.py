import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.common')
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
        """Shorten a string containing a newline and ensure newline is escaped and string is truncated."""
        # input contains a newline which should become two characters: '\' and 'n'
        original = "abcdef\nghijkl"
        # choose a small max_length to trigger truncation
        shortened = _shorten_strings(original, max_length=10)
        # After replacement: "abcdef\\nghijkl"
        # max_length - 3 = 7 -> take first 7 chars "abcdef\" and append "..."
        expected = "abcdef\\..."
        self.assertEqual(shortened, expected)
