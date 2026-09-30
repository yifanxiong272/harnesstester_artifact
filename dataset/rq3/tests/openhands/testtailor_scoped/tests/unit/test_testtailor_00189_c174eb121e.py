import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.security.grayswan.analyzer')
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
        """Missing GRAYSWAN_API_KEY should raise ValueError during initialization."""
        # Backup and remove any existing API key from environment
        original_api_key = os.environ.pop('GRAYSWAN_API_KEY', None)
        try:
            with self.assertRaises(ValueError) as cm:
                GraySwanAnalyzer()
            self.assertIn('GRAYSWAN_API_KEY', str(cm.exception))
        finally:
            # Restore original environment state
            if original_api_key is not None:
                os.environ['GRAYSWAN_API_KEY'] = original_api_key
