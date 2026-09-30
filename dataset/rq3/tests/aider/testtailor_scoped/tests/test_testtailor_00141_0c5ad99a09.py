import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.utils')
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
        """Test that a message with a function_call produces the expected Function Call line."""
        messages = [
            {"role": "assistant", "content": "OK", "function_call": "my_func(1)"}
        ]

        result = format_messages(messages)

        # Function call line should be present and correctly prefixed with the uppercased role
        self.assertIn("ASSISTANT Function Call: my_func(1)", result)

        # Content should still be formatted and present
        self.assertIn("ASSISTANT OK", result)

        # Ensure content appears before the function call line
        self.assertLess(
            result.find("ASSISTANT OK"), result.find("ASSISTANT Function Call: my_func(1)")
        )
