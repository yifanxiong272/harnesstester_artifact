import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.server.conversation_manager.standalone_conversation_manager')
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
        """Test _last_updated_at_key returns 0.0 for None and the timestamp for a datetime."""
        # Conversation with no last_updated_at should return 0.0
        mock_conversation_none = MagicMock()
        mock_conversation_none.last_updated_at = None
        result_none = _last_updated_at_key(mock_conversation_none)
        self.assertEqual(result_none, 0.0)

        # Conversation with a datetime should return its timestamp
        dt = datetime(2020, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
        mock_conversation_dt = MagicMock()
        mock_conversation_dt.last_updated_at = dt
        result_dt = _last_updated_at_key(mock_conversation_dt)
        self.assertEqual(result_dt, dt.timestamp())
