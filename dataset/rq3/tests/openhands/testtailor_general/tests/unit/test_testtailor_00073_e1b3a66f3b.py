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
        """Ensure save_to_session deletes the old (no-user) filename when user_id is provided."""
        # Arrange
        sid = 'test-session-xyz'
        user_id = 'user-123'

        # Create a FileStore mock that implements the required interface
        file_store = MagicMock(spec=FileStore)
        # Make write a no-op (but record calls)
        file_store.write.return_value = None
        # Make delete a no-op (but record calls)
        file_store.delete.return_value = None

        # Create a State instance with some conversation_stats set (will be nulled during save)
        state = State()
        state.session_id = sid
        sentinel_stats = object()
        state.conversation_stats = sentinel_stats
        state.agent_state = AgentState.RUNNING

        # Act
        state.save_to_session(sid, file_store, user_id)

        # Assert: write was called for the user-specific path
        expected_write_path = get_conversation_agent_state_filename(sid, user_id)
        file_store.write.assert_called_once()
        written_path = file_store.write.call_args[0][0]
        self.assertEqual(written_path, expected_write_path)

        # Assert: delete was called for the old (no-user) path
        expected_old_path = get_conversation_agent_state_filename(sid)
        file_store.delete.assert_called_once_with(expected_old_path)

        # Ensure conversation_stats reference was restored after save
        self.assertIs(state.conversation_stats, sentinel_stats)
