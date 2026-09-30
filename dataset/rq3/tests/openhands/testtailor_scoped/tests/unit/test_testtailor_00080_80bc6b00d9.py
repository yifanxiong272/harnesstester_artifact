import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.server.routes.manage_conversations')
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
        """Test that conversations missing created_at are skipped by the age filter."""
        # Create a fake conversation object without a created_at attribute
        FakeConv = type("FakeConv", (), {"conversation_id": "conv_no_created"})
        convo_without_created = FakeConv()

        # Sanity: ensure the object truly lacks created_at
        self.assertFalse(hasattr(convo_without_created, "created_at"))

        # Call the function under test with the conversation that lacks created_at
        filtered = _filter_conversations_by_age([convo_without_created], max_age_seconds=3600)

        # Expect the conversation to be skipped and the result to be empty
        self.assertEqual(filtered, [])
