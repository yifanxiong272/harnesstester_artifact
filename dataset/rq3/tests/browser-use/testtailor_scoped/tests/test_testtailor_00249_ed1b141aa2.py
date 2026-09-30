import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.judge')
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
        """When text length is less than or equal to max_length, the original text is returned unchanged."""
        short_text = "keep me"
        # Case: max_length greater than length of text
        result = _truncate_text(short_text, max_length=20)
        self.assertEqual(result, short_text)
        # Case: max_length equal to length of text (edge)
        result_equal = _truncate_text(short_text, max_length=len(short_text), from_beginning=True)
        self.assertEqual(result_equal, short_text)
