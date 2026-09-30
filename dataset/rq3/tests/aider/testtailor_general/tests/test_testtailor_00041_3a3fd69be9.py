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
        """System messages should be ignored during alternation checks.
        Verify a list with only a system message returns False (no non-system last role),
        and a list with a system message followed by a user message returns True.
        """
        from aider.sendchat import sanity_check_messages

        # Only a system message -> no non-system last role, should return False
        messages_only_system = [{"role": "system", "content": "init"}]
        assert sanity_check_messages(messages_only_system) is False

        # System message followed by a user message -> last non-system is user, should return True
        messages_system_then_user = [
            {"role": "system", "content": "init"},
            {"role": "user", "content": "Hello"},
        ]
        assert sanity_check_messages(messages_system_then_user) is True
