import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.tools.service')
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
        """Verify that an old-format sensitive key/value pair returns the key."""
        # Old format: {key: value} where value is a plain string
        sensitive = {'api_key': 'secret123', 'other': 'value'}
        result = _detect_sensitive_key_name('secret123', sensitive)
        self.assertEqual(result, 'api_key')

        # Also verify non-matching text returns None
        self.assertIsNone(_detect_sensitive_key_name('nope', sensitive))

        # And verify that None or empty text returns None
        self.assertIsNone(_detect_sensitive_key_name('', sensitive))
        self.assertIsNone(_detect_sensitive_key_name('secret123', None))
