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
        """Return STARTING when agent_session.runtime exists but is not initialized."""
        # Prepare a mocked session with an agent_session whose runtime is present
        # but not initialized (runtime_initialized == False).
        session = MagicMock()
        agent_session = MagicMock()
        runtime = MagicMock()
        runtime.runtime_initialized = False  # Not initialized -> should yield STARTING
        agent_session.runtime = runtime
        session.agent_session = agent_session

        status = _get_status_from_session(session)

        self.assertEqual(status, ConversationStatus.STARTING)
