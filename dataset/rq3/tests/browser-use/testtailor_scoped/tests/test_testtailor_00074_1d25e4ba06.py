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
        """Verify prefix construction and truncation behavior in _log_format_message_line."""
        # Create a dummy message whose class name matches the emoji mapping key
        class UserMessage:
            pass

        message = UserMessage()

        # Case 1: content fits within content_width -> no truncation
        content = "hello world"
        terminal_width = 40  # content_width = 30
        lines = _log_format_message_line(message, content, is_last_message=False, terminal_width=terminal_width)

        self.assertIsInstance(lines, list)
        self.assertEqual(len(lines), 1)
        expected_prefix = "💬[??? (TODO)]: "
        self.assertEqual(lines[0], expected_prefix + content)

        # Case 2: content longer than content_width -> gets truncated for single-line branch
        long_content = "abcdefghijklmnopqrstuvwxyz"
        terminal_width_small = 20  # content_width = 10
        lines2 = _log_format_message_line(message, long_content, is_last_message=False, terminal_width=terminal_width_small)

        self.assertIsInstance(lines2, list)
        self.assertEqual(len(lines2), 1)
        expected_truncated = long_content[: (terminal_width_small - 10)]
        self.assertEqual(lines2[0], expected_prefix + expected_truncated)
