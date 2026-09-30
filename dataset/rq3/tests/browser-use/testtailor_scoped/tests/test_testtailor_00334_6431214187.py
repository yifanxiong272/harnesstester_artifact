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
        """Trigger the branch that truncates the 'rest' line (executes `rest = rest[: terminal_width - 10]`)."""
        terminal_width = 20  # small width to force wrapping and truncation
        # content length > 2 * content_width to ensure `len(rest) > terminal_width - 10`
        content = 'A' * 25

        # Create a lightweight message object whose class name matches the emoji mapping
        message = type('UserMessage', (), {})()

        lines = _log_format_message_line(message, content, True, terminal_width)

        # Expect two lines: first the prefixed first chunk, second the indented truncated rest
        self.assertEqual(len(lines), 2)

        prefix = _log_get_message_emoji(message) + '[??? (TODO)]: '
        # content_width = terminal_width - 10 = 10
        self.assertEqual(lines[0], prefix + 'A' * 10)
        # second line should be indented by 10 spaces and contain at most terminal_width - 10 (10) chars
        self.assertEqual(lines[1], ' ' * 10 + 'A' * 10)
