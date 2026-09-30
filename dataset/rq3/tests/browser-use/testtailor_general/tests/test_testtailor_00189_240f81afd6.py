import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.views')
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
        """Ensure ValueError is raised when both trigger_char_count and trigger_token_count are set."""
        # Both values set should trigger the validator to raise a ValueError.
        with self.assertRaises(ValueError) as cm:
            MessageCompactionSettings(trigger_char_count=1000, trigger_token_count=250)

        # Verify the error message mentions the mutually exclusive setting.
        self.assertIn('trigger_char_count or trigger_token_count', str(cm.exception))
