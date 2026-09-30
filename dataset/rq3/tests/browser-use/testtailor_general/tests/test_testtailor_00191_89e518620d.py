import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.message_manager.service')
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
        """Verify prefix construction and wrapping behavior in _log_format_message_line"""
        # create a simple message-like object with the desired class name for emoji lookup
        class UserMessage:
            pass

        msg = UserMessage()

        # Case 1: short content, not last message -> single-line output, no truncation
        terminal_width = 40
        content = "Hello world"
        lines = _log_format_message_line(msg, content, is_last_message=False, terminal_width=terminal_width)

        expected_prefix = "💬[??? (TODO)]: "
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], expected_prefix + content)

        # Case 2: last message long enough to trigger wrapping at a good break point
        # terminal_width=40 -> content_width = 30. We place a space at index 25 (> 30*0.7 = 21)
        first_part = "x" * 25
        rest_part = "this is the remainder of the message"
        long_content = first_part + " " + rest_part  # break_point should be at 25
        lines = _log_format_message_line(msg, long_content, is_last_message=True, terminal_width=terminal_width)

        # Expect two lines: prefix + first_part, then 10-space indent + rest_part (possibly truncated)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], expected_prefix + first_part)
        self.assertTrue(lines[1].startswith(" " * 10))
        self.assertEqual(lines[1].lstrip(), rest_part[: terminal_width - 10])
