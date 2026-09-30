import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.sync.service')
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
        """Verify CloudSync constructor sets base_url, auth_client and flags correctly."""
        # Preserve original config and restore afterwards
        orig_url = CONFIG.BROWSER_USE_CLOUD_API_URL
        orig_sync = CONFIG.BROWSER_USE_CLOUD_SYNC
        try:
            # Set deterministic config values for the test
            CONFIG.BROWSER_USE_CLOUD_API_URL = 'https://api.example.test'
            CONFIG.BROWSER_USE_CLOUD_SYNC = True

            # Default construction should pick up CONFIG.BROWSER_USE_CLOUD_API_URL
            cs_default = CloudSync()
            self.assertEqual(cs_default.base_url, 'https://api.example.test')
            self.assertIsNotNone(cs_default.auth_client)
            # auth_client should be constructed with same base_url
            self.assertEqual(cs_default.auth_client.base_url, cs_default.base_url)
            # Initial session_id should be None
            self.assertIsNone(cs_default.session_id)
            # Default allow_session_events_for_auth is False
            self.assertFalse(cs_default.allow_session_events_for_auth)
            # Auth flow should start as inactive
            self.assertFalse(cs_default.auth_flow_active)
            # enabled should reflect CONFIG
            self.assertTrue(cs_default.enabled)

            # Passing explicit base_url and flag should override config/defaults
            cs_custom = CloudSync(base_url='https://custom.example', allow_session_events_for_auth=True)
            self.assertEqual(cs_custom.base_url, 'https://custom.example')
            self.assertEqual(cs_custom.auth_client.base_url, 'https://custom.example')
            self.assertTrue(cs_custom.allow_session_events_for_auth)
            self.assertIsNone(cs_custom.session_id)
            self.assertFalse(cs_custom.auth_flow_active)
            self.assertTrue(cs_custom.enabled)

        finally:
            CONFIG.BROWSER_USE_CLOUD_API_URL = orig_url
            CONFIG.BROWSER_USE_CLOUD_SYNC = orig_sync
