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
        """Trigger the branch where is_last_message is True, content longer than content_width,
        but no good break point is found (so code falls into the 'No good break point, just truncate' path)."""
        # Create a minimal message class named 'UserMessage' so _log_get_message_emoji returns 💬
        class UserMessage:
            pass

        msg = UserMessage()

        # Choose terminal width so content_width = terminal_width - 10 is small
        terminal_width = 40
        content_width = terminal_width - 10

        # Create content longer than content_width with NO spaces so rfind returns -1 (no good break point)
        content = 'A' * (content_width + 5)  # e.g., 30 + 5 = 35 chars

        # Call the formatter with is_last_message True to exercise the two-line truncation path
        lines = _log_format_message_line(msg, content, is_last_message=True, terminal_width=terminal_width)

        # Build expected values
        emoji = '💬'  # mapping for class name 'UserMessage'
        token_str = '??? (TODO)'
        prefix = f'{emoji}[{token_str}]: '
        expected_first = prefix + content[:content_width]
        expected_second = ' ' * 10 + content[content_width:]

        # Assert it produced two lines as expected and contents match
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], expected_first)
        self.assertEqual(lines[1], expected_second)
