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
        """sanity_check_messages should raise ValueError when two consecutive non-system messages share the same role"""
        from aider.sendchat import sanity_check_messages

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "user", "content": "Are you there?"},
        ]

        with self.assertRaises(ValueError) as cm:
            sanity_check_messages(messages)

        err = str(cm.exception)
        self.assertIn("Messages don't properly alternate user/assistant", err)
        # Ensure the formatted messages are included in the raised message
        self.assertIn("Hello", err)
        self.assertIn("Are you there?", err)
