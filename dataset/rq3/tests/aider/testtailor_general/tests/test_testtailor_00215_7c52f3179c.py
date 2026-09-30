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
        """Verify show_messages prints formatted output produced by format_messages."""
        messages = [
            {"role": "user", "content": "Hello\nHow are you?"},
            {
                "role": "assistant",
                "content": [
                    "Image",
                    {"file": {"url": "http://example.com/img.png"}},
                    {"meta": "value"},
                ],
            },
            {"role": "system", "content": "System message"},
            {"role": "assistant", "content": "Done", "function_call": "do_something()"},
        ]
        title = "Conversation"

        with patch("builtins.print") as mock_print:
            show_messages(messages, title=title, functions=None)

        # Build expected output the same way format_messages would
        expected_lines = []
        expected_lines.append(f"{title.upper()} {'*' * 50}")
        # user message
        expected_lines.append("-------")
        expected_lines.append("USER Hello")
        expected_lines.append("USER How are you?")
        # assistant list content
        expected_lines.append("-------")
        expected_lines.append("ASSISTANT Image")
        expected_lines.append("ASSISTANT File URL: http://example.com/img.png")
        expected_lines.append("ASSISTANT meta: value")
        # system message
        expected_lines.append("-------")
        expected_lines.append("SYSTEM System message")
        # assistant with function call
        expected_lines.append("-------")
        expected_lines.append("ASSISTANT Done")
        expected_lines.append("ASSISTANT Function Call: do_something()")

        expected = "\n".join(expected_lines)

        mock_print.assert_called_once_with(expected)
