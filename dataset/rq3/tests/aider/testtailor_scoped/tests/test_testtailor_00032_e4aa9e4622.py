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
        """Sanity check should skip system messages and return True when the last non-system role is user."""
        from aider.sendchat import sanity_check_messages

        messages = [
            {"role": "system", "content": "init"},
            {"role": "user", "content": "Hello"},
            {"role": "system", "content": "meta"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "Goodbye"},
        ]

        result = sanity_check_messages(messages)
        assert result is True
