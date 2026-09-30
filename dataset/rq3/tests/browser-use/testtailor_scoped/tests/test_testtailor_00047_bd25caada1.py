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
        """Detect_variables_in_history should skip history items with no model_output and return empty dict."""
        # Create a dummy history item with no model_output
        class DummyHistoryItem:
            pass

        item = DummyHistoryItem()
        item.model_output = None
        item.state = None

        # Create a history-like object with a single item
        class DummyHistoryList:
            pass

        history = DummyHistoryList()
        history.history = [item]

        # Call the function under test
        detected = detect_variables_in_history(history)  # type: ignore[name-defined]

        # Expect no variables detected because the only history item has no model_output
        self.assertIsInstance(detected, dict)
        self.assertEqual(detected, {})
