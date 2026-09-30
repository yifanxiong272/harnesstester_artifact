import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.sendchat')
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
        """Verify sanity_check_messages raises ValueError when two consecutive non-system messages have the same role."""
        from aider.sendchat import sanity_check_messages
        from aider.utils import format_messages

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "user", "content": "Are you there?"},
            {"role": "assistant", "content": "Yes"},
        ]

        with self.assertRaises(ValueError) as cm:
            sanity_check_messages(messages)

        err_str = str(cm.exception)
        self.assertIn("Messages don't properly alternate user/assistant", err_str)

        # Ensure the formatted turns from format_messages are included in the error message
        expected_turns = format_messages(messages)
        self.assertIn(expected_turns, err_str)
