import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.patch_coder')
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
        """Strip CR so comparisons work for both LF and CRLF input."""
        # No CR: unchanged
        self.assertEqual(_norm("abc\n"), "abc\n")
        # Single trailing CR removed
        self.assertEqual(_norm("abc\r"), "abc")
        # CR before LF is not removed by rstrip("\r") (trailing char is \n), so CRLF stays CRLF
        self.assertEqual(_norm("abc\r\n"), "abc\r\n")
        # Multiple trailing CRs all removed
        self.assertEqual(_norm("abc\r\r"), "abc")
        # Internal CRs are preserved; only trailing CR characters are removed
        self.assertEqual(_norm("a\rb\rc\r\n"), "a\rb\rc\r\n")
        # Empty string stays empty
        self.assertEqual(_norm(""), "")
        # Only CRs -> empty string
        self.assertEqual(_norm("\r\r"), "")
