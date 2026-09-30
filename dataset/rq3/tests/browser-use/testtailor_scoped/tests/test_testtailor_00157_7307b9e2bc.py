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
        """Detect variables when actions are plain dicts (no model_dump)"""
        # Create a dict action (no model_dump) so code path uses isinstance(action, dict)
        action = {'input': {'text': 'old@example.com'}}

        # Minimal classes to mimic expected structure without imports
        class ModelOutput:
            def __init__(self, action_list):
                self.action = action_list

        class State:
            def __init__(self, interacted_element):
                self.interacted_element = interacted_element

        class HistoryItem:
            def __init__(self, model_output, state):
                self.model_output = model_output
                self.state = state

        class HistoryContainer:
            def __init__(self, history_items):
                self.history = history_items

        # Element with attributes so element-based detection picks up email
        element = type('E', (), {})()
        element.attributes = {'type': 'email'}

        model_output = ModelOutput([action])
        state = State([element])
        history_item = HistoryItem(model_output, state)
        history = HistoryContainer([history_item])

        # Call the function under test
        detected = detect_variables_in_history(history)

        # Expect an 'email' variable detected from the dict action
        self.assertIn('email', detected)
        dv = detected['email']
        self.assertEqual(dv.original_value, 'old@example.com')
        self.assertEqual(dv.format, 'email')
        self.assertEqual(dv.type, 'string')
