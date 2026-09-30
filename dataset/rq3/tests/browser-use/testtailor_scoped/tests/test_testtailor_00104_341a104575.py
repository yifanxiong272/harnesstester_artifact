import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.variable_detector')
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
        """Ensure branch where action has model_dump() is taken and detection works."""
        # Create an action-like object that exposes model_dump()
        class MockActionWithModelDump:
            def model_dump(self):
                # Shape matches expected action dict: { action_name: { params } }
                return {'input': {'index': 1, 'text': 'old@example.com'}}

        # Minimal model_output/state/history container classes
        class MockModelOutput:
            def __init__(self, action):
                # Accept 'action' as a keyword or positional argument
                self.action = action

        class MockState:
            def __init__(self, interacted_element):
                self.interacted_element = interacted_element

        class MockHistoryItem:
            def __init__(self, model_output, state):
                self.model_output = model_output
                self.state = state

        class MockHistory:
            def __init__(self, history):
                self.history = history

        # Provide an interacted element with attributes so attribute-based detection triggers
        class MockElement:
            def __init__(self, attributes):
                self.attributes = attributes

        mock_action = MockActionWithModelDump()
        # pass action list using keyword to mirror real usage
        mock_model_output = MockModelOutput(action=[mock_action])
        interacted_element = MockElement(attributes={'type': 'email'})
        mock_state = MockState(interacted_element=[interacted_element])
        mock_history_item = MockHistoryItem(model_output=mock_model_output, state=mock_state)
        mock_history = MockHistory(history=[mock_history_item])

        # Call the target function; this should call action.model_dump() internally
        detected = detect_variables_in_history(mock_history)  # type: ignore[name-defined]

        # Assertions: detection should find an 'email' variable with the original value and format
        self.assertIn('email', detected)
        self.assertEqual(detected['email'].original_value, 'old@example.com')
        self.assertEqual(detected['email'].format, 'email')
