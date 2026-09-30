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
        """Ensure ChatSummary.__init__ raises when no models are provided."""
        # models is None
        with self.subTest("models is None"):
            with self.assertRaises(ValueError) as cm:
                ChatSummary(models=None)
            self.assertEqual(str(cm.exception), "At least one model must be provided")

        # models is empty list
        with self.subTest("models is empty list"):
            with self.assertRaises(ValueError) as cm:
                ChatSummary(models=[])
            self.assertEqual(str(cm.exception), "At least one model must be provided")
