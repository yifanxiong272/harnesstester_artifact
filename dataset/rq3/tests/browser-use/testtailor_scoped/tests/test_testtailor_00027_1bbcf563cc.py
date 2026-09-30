import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.prompts')
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
        """_is_anthropic_4_5_model returns False when model_name is falsy (None or empty)."""
        # None should trigger the early return False
        self.assertFalse(_is_anthropic_4_5_model(None))
        # Empty string should also be considered falsy and return False
        self.assertFalse(_is_anthropic_4_5_model(''))
