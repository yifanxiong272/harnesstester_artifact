import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.core.config.mcp_config')
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
        """Validate that an empty or whitespace-only URL raises the expected ValueError."""
        # whitespace-only URL
        with self.assertRaisesRegex(ValueError, r'^URL cannot be empty$'):
            _validate_mcp_url('   ')
        # empty string URL
        with self.assertRaisesRegex(ValueError, r'^URL cannot be empty$'):
            _validate_mcp_url('')
