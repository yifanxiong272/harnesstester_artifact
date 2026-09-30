import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.gif')
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
        """When history.screenshots() returns an empty list, create_history_gif should return early (None)."""
        # Dummy history-like object with a non-empty .history so the early "no history" checks pass,
        # but its screenshots() method returns an empty list to trigger the target branch.
        class DummyHistory:
            def __init__(self):
                self.history = [object()]

            def screenshots(self, *args, **kwargs):
                return []

        dummy_history = DummyHistory()

        # Call the function and assert it returns None (early return when no screenshots found)
        result = create_history_gif(task='Do something', history=dummy_history, output_path='unused.gif', duration=10)
        self.assertIsNone(result)
