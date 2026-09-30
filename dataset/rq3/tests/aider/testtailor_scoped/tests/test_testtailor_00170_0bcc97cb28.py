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
        """Verify show_messages formats messages and prints the formatted output."""
        messages = [
            {
                "role": "user",
                "content": [
                    {"image": {"url": "http://example.com/img.png"}},
                    "extra item"
                ],
            },
            {
                "role": "assistant",
                "content": "Hello\nWorld",
                "function_call": "do_something()",
            },
        ]
        title = "My Test"

        # Compute expected formatted output using the real formatter
        expected = format_messages(messages, title)

        # Patch print and call show_messages, then assert print was called with the formatted output
        with patch("builtins.print") as mock_print:
            show_messages(messages, title=title)

        # Ensure print was invoked exactly once with the formatted output
        mock_print.assert_called_once_with(expected)
