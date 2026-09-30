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
        """ReplayManager should ignore ENVIRONMENT events and NullObservation, and override wait_for_response for non-last MessageAction."""
        # environment event should be ignored
        env_event = MessageAction(content='from_env')
        env_event._source = EventSource.ENVIRONMENT

        # NullObservation should be ignored (provide required content argument)
        null_obs = NullObservation(content='noop')
        null_obs._source = EventSource.AGENT

        # First message waits for response but is not the last after filtering,
        # so wait_for_response should be overridden to False
        msg1 = MessageAction(content='first_message', wait_for_response=True)
        msg1._source = EventSource.USER

        # Second message (last) should keep its wait_for_response value
        msg2 = MessageAction(content='second_message', wait_for_response=False)
        msg2._source = EventSource.AGENT

        rm = ReplayManager([env_event, null_obs, msg1, msg2])

        # ENVIRONMENT event and NullObservation should be filtered out
        self.assertTrue(rm.replay_mode)
        self.assertEqual(len(rm.replay_events), 2)

        # The remaining events should be msg1 and msg2 in order
        self.assertIs(rm.replay_events[0], msg1)
        self.assertIs(rm.replay_events[1], msg2)

        # msg1.wait_for_response should have been overridden to False because it's not the last replay event
        self.assertFalse(rm.replay_events[0].wait_for_response)

        # replay_index should be initialized to 0
        self.assertEqual(rm.replay_index, 0)
