import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.storage.conversation.file_conversation_store')
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
        """When conversation.created_at is None, _sort_key returns an empty string."""
        # Create a minimal stub with a created_at attribute set to None
        ConversationStub = type("ConversationStub", (), {})
        convo = ConversationStub()
        convo.created_at = None

        result = _sort_key(convo)
        self.assertEqual(result, "")
