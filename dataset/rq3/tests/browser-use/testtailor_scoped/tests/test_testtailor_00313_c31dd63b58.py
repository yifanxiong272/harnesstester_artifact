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
        """When element context is missing and the value doesn't match any pattern,
        _detect_in_action should not add anything to detected or detected_values.
        """
        # Prepare inputs: a single action with a text value that should not be detected
        action_dict = {'some_action': {'text': 'not_a_variable'}}  # lowercase, not an email/phone/date/number/name
        element = None  # No element context so attribute-based detection is skipped
        detected: dict[str, DetectedVariable] = {}
        detected_values: set[str] = set()

        # Call function under test
        _detect_in_action(action_dict, element, detected, detected_values)

        # Expect no detection to have occurred
        self.assertEqual(detected, {})
        self.assertEqual(detected_values, set())
