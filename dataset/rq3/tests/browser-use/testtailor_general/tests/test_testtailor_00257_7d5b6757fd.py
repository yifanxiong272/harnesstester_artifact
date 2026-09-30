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
    def test_action_model_dump_branch(self):
        """Ensure detect_variables_in_history uses action.model_dump() when available"""
        # Create an action object that exposes model_dump()
        class ActionWithModelDump:
            def model_dump(self):
                # Structure expected by _detect_in_action: action_type -> params (with 'text' or 'query')
                return {'input': {'text': 'old@example.com'}}

        # Minimal container objects to mimic history structure expected by the function
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

        class HistoryList:
            def __init__(self, items):
                self.history = items

        # Create a lightweight element object with attributes dict so attribute-based detection works.
        class SimpleElement:
            def __init__(self, attributes):
                self.attributes = attributes

        element = SimpleElement({'type': 'email'})

        action = ActionWithModelDump()
        model_output = ModelOutput([action])
        state = State([element])
        history_item = HistoryItem(model_output, state)
        history = HistoryList([history_item])

        # Call the function under test
        detected = detect_variables_in_history(history)  # type: ignore[arg-type]

        # Expect a detected variable named 'email' with the original value from the action
        self.assertIn('email', detected)
        detected_var = detected['email']
        self.assertEqual(detected_var.original_value, 'old@example.com')
        self.assertEqual(detected_var.format, 'email')
