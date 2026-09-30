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
        """Test collapse_repeats with a variety of inputs, including edge cases."""
        # empty string
        self.assertEqual(collapse_repeats(""), "")

        # single character
        self.assertEqual(collapse_repeats("a"), "a")

        # contiguous runs collapse
        self.assertEqual(collapse_repeats("aaabbbccc"), "abc")

        # non-contiguous repeats remain
        self.assertEqual(collapse_repeats("ababab"), "ababab")

        # mixed runs
        self.assertEqual(collapse_repeats("aabbbaa"), "aba")

        # digits
        self.assertEqual(collapse_repeats("111122233"), "123")

        # unicode characters
        self.assertEqual(collapse_repeats("éééèèé"), "éèé")

        # whitespace and newlines
        self.assertEqual(collapse_repeats(" \n\n \n"), " \n \n")
