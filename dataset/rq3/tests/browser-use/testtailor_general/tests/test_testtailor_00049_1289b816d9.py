import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.integrations.gmail.service')
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
        """Ensure default config_dir uses CONFIG.BROWSER_USE_CONFIG_DIR when None"""
        # Provide an access token to avoid filesystem mkdir side-effects
        gmail_service = GmailService(access_token="dummy-token")

        # When config_dir is None, __init__ should set it to CONFIG.BROWSER_USE_CONFIG_DIR
        self.assertEqual(gmail_service.config_dir, CONFIG.BROWSER_USE_CONFIG_DIR)

        # Access token should be preserved
        self.assertEqual(gmail_service.access_token, "dummy-token")

        # Default credential/token filenames should be derived from the config_dir
        self.assertTrue(str(gmail_service.credentials_file).endswith('gmail_credentials.json'))
        self.assertTrue(str(gmail_service.token_file).endswith('gmail_token.json'))
