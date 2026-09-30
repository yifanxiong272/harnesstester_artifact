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
        """Return STARTING when the agent runtime is missing or not initialized."""
        # Session with no runtime -> should be STARTING
        session = MagicMock()
        agent_session = MagicMock()
        agent_session.runtime = None
        session.agent_session = agent_session

        status = _get_status_from_session(session)
        self.assertEqual(status, ConversationStatus.STARTING)

        # Session with runtime present but not initialized -> still STARTING
        runtime = MagicMock()
        runtime.runtime_initialized = False
        agent_session.runtime = runtime
        status2 = _get_status_from_session(session)
        self.assertEqual(status2, ConversationStatus.STARTING)
