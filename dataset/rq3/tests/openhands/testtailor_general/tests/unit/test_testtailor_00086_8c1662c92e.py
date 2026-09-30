import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.controller.replay')
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
        """Ensure ENVIRONMENT events are ignored by ReplayManager.__init__."""
        # Create an environment event that should be ignored
        env_event = Event()
        setattr(env_event, '_source', EventSource.ENVIRONMENT)

        # Create a user message action that should be kept
        user_event = MessageAction(content='hello')
        setattr(user_event, '_source', EventSource.USER)

        # ReplayManager with both events: ENVIRONMENT should be filtered out,
        # only the user event should remain.
        mgr = ReplayManager([env_event, user_event])
        self.assertTrue(mgr.replay_mode)
        self.assertEqual(len(mgr.replay_events), 1)
        self.assertIsInstance(mgr.replay_events[0], MessageAction)
        self.assertEqual(mgr.replay_index, 0)

        # ReplayManager with only an ENVIRONMENT event: replay_events should be empty
        mgr_only_env = ReplayManager([env_event])
        self.assertFalse(mgr_only_env.replay_mode)
        self.assertEqual(mgr_only_env.replay_events, [])
        self.assertEqual(mgr_only_env.replay_index, 0)
