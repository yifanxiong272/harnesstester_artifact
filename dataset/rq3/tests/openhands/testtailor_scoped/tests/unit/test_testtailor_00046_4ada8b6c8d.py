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
        """Ensure GraySwanAnalyzer reads GRAYSWAN_API_KEY and falls back to default policy id."""
        prev_api = os.environ.get('GRAYSWAN_API_KEY')
        prev_policy = os.environ.get('GRAYSWAN_POLICY_ID')
        try:
            # Set required environment variable and ensure policy id is not set
            os.environ['GRAYSWAN_API_KEY'] = 'dummy_key_123'
            if 'GRAYSWAN_POLICY_ID' in os.environ:
                del os.environ['GRAYSWAN_POLICY_ID']

            analyzer = GraySwanAnalyzer()

            # Verify api_key was read from the environment
            self.assertEqual(analyzer.api_key, 'dummy_key_123')

            # Verify default policy id is used when GRAYSWAN_POLICY_ID is not set
            self.assertEqual(analyzer.policy_id, '689ca4885af3538a39b2ba04')

            # Basic sanity checks for other initialized attributes
            self.assertEqual(analyzer.history_limit, 20)
            self.assertEqual(analyzer.max_message_chars, 30000)
            self.assertEqual(analyzer.timeout, 30)
            self.assertIsNone(analyzer.session)
            self.assertEqual(analyzer.api_url, 'https://api.grayswan.ai/cygnal/monitor')
            self.assertIn('low', analyzer.violation_thresholds)
            self.assertIn('medium', analyzer.violation_thresholds)
            self.assertIn('high', analyzer.violation_thresholds)
        finally:
            # Restore environment
            if prev_api is None:
                if 'GRAYSWAN_API_KEY' in os.environ:
                    del os.environ['GRAYSWAN_API_KEY']
            else:
                os.environ['GRAYSWAN_API_KEY'] = prev_api

            if prev_policy is None:
                if 'GRAYSWAN_POLICY_ID' in os.environ:
                    del os.environ['GRAYSWAN_POLICY_ID']
            else:
                os.environ['GRAYSWAN_POLICY_ID'] = prev_policy
