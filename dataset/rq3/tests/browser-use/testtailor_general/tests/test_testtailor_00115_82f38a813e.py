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
        """When a history item has no model_output, detect_variables_in_history should skip it and return empty dict."""
        # Create minimal dummy objects so we don't need imports like SimpleNamespace
        class DummyHistoryItem:
            pass

        class DummyHistoryList:
            def __init__(self, items):
                self.history = items

        # Single history item with no model_output (falsy) to trigger the branch
        item = DummyHistoryItem()
        item.model_output = None
        item.state = None

        history = DummyHistoryList([item])

        result = detect_variables_in_history(history)
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {})
