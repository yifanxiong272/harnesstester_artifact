import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.history')
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
        """ChatSummary.__init__ should raise when no models are provided (None or empty)."""
        # None should raise
        with self.assertRaises(ValueError) as cm_none:
            ChatSummary(models=None)
        self.assertEqual(str(cm_none.exception), "At least one model must be provided")

        # Empty list should also raise
        with self.subTest("empty list"):
            with self.assertRaises(ValueError) as cm_empty:
                ChatSummary(models=[])
            self.assertEqual(str(cm_empty.exception), "At least one model must be provided")
