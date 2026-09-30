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
        """Initializing GraySwanAnalyzer without GRAYSWAN_API_KEY raises ValueError."""
        # Ensure the env var is not set for this test
        previous = os.environ.pop('GRAYSWAN_API_KEY', None)
        try:
            with self.assertRaises(ValueError) as cm:
                GraySwanAnalyzer()
            self.assertIn('GRAYSWAN_API_KEY', str(cm.exception))
        finally:
            # Restore environment to avoid side effects on other tests
            if previous is not None:
                os.environ['GRAYSWAN_API_KEY'] = previous
