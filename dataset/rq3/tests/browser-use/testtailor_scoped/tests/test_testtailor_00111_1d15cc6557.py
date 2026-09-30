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
        """Detects key name when sensitive_data uses domain->dict mapping and value equals text"""
        # Prepare sensitive_data with the new format: {domain: {key: value}}
        sensitive_data = {
            'example.com': {
                'password': 's3cr3t-value',
                'token': '',
            },
            # include an old-format entry to ensure it does not interfere
            'legacy_key': 'legacy-value',
        }

        # Should find the inner key 'password' because its value matches the text
        found = _detect_sensitive_key_name('s3cr3t-value', sensitive_data)
        self.assertEqual(found, 'password')

        # Ensure non-matching text returns None
        not_found = _detect_sensitive_key_name('nope', sensitive_data)
        self.assertIsNone(not_found)
