import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.controller.state.state')
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
        """Verify save_to_session deletes old non-user-specific file when user_id is provided."""
        # Create a State and set a sentinel conversation_stats to ensure it is restored after save
        state = State()
        sentinel_stats = object()
        state.conversation_stats = sentinel_stats

        sid = 'test-sid-123'
        user_id = 'user-abc'

        # Use a MagicMock FileStore to observe write/delete calls
        fs = MagicMock(spec=FileStore)

        # Call the method under test
        state.save_to_session(sid, fs, user_id)

        # Expected filenames
        expected_new = get_conversation_agent_state_filename(sid, user_id)
        expected_old = get_conversation_agent_state_filename(sid)

        # Verify write was called with the user-specific filename and a string payload
        fs.write.assert_called_once()
        write_args = fs.write.call_args[0]
        self.assertEqual(write_args[0], expected_new)
        self.assertIsInstance(write_args[1], str)

        # Verify delete was attempted on the old filename (without user_id)
        fs.delete.assert_called_once_with(expected_old)

        # Ensure conversation_stats was restored after saving
        self.assertIs(state.conversation_stats, sentinel_stats)
