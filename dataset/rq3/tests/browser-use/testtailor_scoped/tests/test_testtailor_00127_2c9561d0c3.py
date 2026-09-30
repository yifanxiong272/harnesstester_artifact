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
        """Exercise the branch where the last message is wrapped at a good break point."""
        # Terminal width chosen so content_width = terminal_width - 10 = 30
        terminal_width = 40
        content_width = terminal_width - 10

        # Build content longer than content_width and with a space at index 25
        content = 'X' * 25 + ' ' + 'Y' * 10  # total length 36 > 30

        # Provide a message object whose class name matches the emoji map key
        class UserMessage:
            pass

        message = UserMessage()

        # Call the function under test
        lines = _log_format_message_line(message, content, True, terminal_width)

        # Recompute break_point exactly as the function does
        break_point = content.rfind(' ', 0, content_width)

        # Ensure we hit the intended branch (good break point > 70% of line)
        self.assertTrue(len(content) > content_width)
        self.assertTrue(break_point > content_width * 0.7)

        first_line = content[:break_point]
        rest = content[break_point + 1 :]

        expected_prefix = '💬[??? (TODO)]: '

        # Expect two lines: prefix + first part, and a 10-space indented remainder
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], expected_prefix + first_line)
        self.assertEqual(lines[1], ' ' * 10 + rest)
