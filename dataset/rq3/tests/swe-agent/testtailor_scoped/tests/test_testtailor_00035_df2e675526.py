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
        """Test that dict branches are processed and strings are shortened (including lists and nested dicts)."""
        input_data = {
            "short": "hey",
            "long": "abcdefghijk\nlmnop",
            "lst": ["0123456789", "a\nb"],
            "nested": {"inner": "1234567890"},
        }

        result = _shorten_strings(input_data, max_length=10)

        expected = {
            # max_length=10 -> take first 7 chars then "..."
            "short": "hey...",
            "long": "abcdefg...",
            "lst": ["0123456...", "a\\nb..."],
            "nested": {"inner": "1234567..."},
        }

        self.assertEqual(result, expected)
