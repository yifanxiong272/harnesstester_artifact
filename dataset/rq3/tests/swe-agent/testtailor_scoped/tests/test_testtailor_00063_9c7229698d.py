import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.history_processors')
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
        """Validate that passing a non-positive n triggers the validator error."""
        with self.assertRaises(Exception) as cm:
            # This should invoke the field validator and raise the ValueError internally,
            # which pydantic will wrap into a validation exception.
            LastNObservations(n=0)
        self.assertIn("n must be a positive integer", str(cm.exception))
