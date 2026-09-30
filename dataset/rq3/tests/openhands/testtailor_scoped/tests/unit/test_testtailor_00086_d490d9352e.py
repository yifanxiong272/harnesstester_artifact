import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.memory.condenser.impl.conversation_window_condenser')
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
    def test_no_first_user_message_triggers_warning_and_empty_condensation(self):
        """If the view has events but no user MessageAction, the condenser should return
        an empty condensation (no forgotten events) and not raise.
        """
        # Create a condenser
        condenser = ConversationWindowCondenser()

        # Create a system message event (non-user) so that the events list is non-empty
        system_message = SystemMessageAction(content='System only')
        system_message._source = EventSource.AGENT
        # Ensure the event has an id so get_condensation can compute sets without error
        system_message._id = 1

        # Create a minimal view-like object with an 'events' attribute
        class DummyView:
            pass

        view = DummyView()
        view.events = [system_message]

        # Call get_condensation - should hit the branch where first_user_msg is None
        condensation = condenser.get_condensation(view)

        # The condenser should return a Condensation whose action indicates nothing is forgotten
        self.assertIsNotNone(condensation)
        self.assertIsInstance(condensation, Condensation)
        self.assertIsNotNone(condensation.action)
        # Because there is no first user message, the implementation returns an empty forgotten list
        self.assertEqual(condensation.action.forgotten_event_ids, [])
