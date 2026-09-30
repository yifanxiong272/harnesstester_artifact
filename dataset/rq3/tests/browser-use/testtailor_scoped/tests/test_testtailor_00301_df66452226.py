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
        """Trigger truncation from the beginning branch and verify result."""
        text = "the quick brown fox jumps over the lazy dog " * 3  # long text
        max_length = 30
        result = _truncate_text(text, max_length, from_beginning=True)
        expected = '...[text truncated]' + text[-max_length + 23 :]
        self.assertEqual(result, expected)
