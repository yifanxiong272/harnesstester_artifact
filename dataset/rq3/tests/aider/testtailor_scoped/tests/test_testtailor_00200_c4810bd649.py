import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.udiff_coder')
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
        """Verify collapse_repeats collapses consecutive identical characters."""
        # basic examples
        self.assertEqual(collapse_repeats("aaabcc"), "abc")
        self.assertEqual(collapse_repeats(""), "")
        self.assertEqual(collapse_repeats("a"), "a")

        # numbers and repeated groups that reappear later
        self.assertEqual(collapse_repeats("11223311"), "1231")

        # whitespace and newlines
        self.assertEqual(collapse_repeats("a   a"), "a a")
        self.assertEqual(collapse_repeats("\n\n\nabc\n\n"), "\nabc\n")

        # punctuation and mixed characters
        self.assertEqual(collapse_repeats("111--222"), "1-2")

        # unicode characters
        self.assertEqual(collapse_repeats("ääääbb"), "äb")
