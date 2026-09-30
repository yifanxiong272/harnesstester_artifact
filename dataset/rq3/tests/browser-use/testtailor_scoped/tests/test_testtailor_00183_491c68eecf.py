import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.aws.chat_anthropic')
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
        """When no session is provided and aws_access_key is set, _get_client_params includes aws_access_key."""
        model = ChatAnthropicBedrock()
        # Ensure no session so branch that uses individual credentials is taken
        model.session = None
        # Set only the access key to hit the target assignment
        model.aws_access_key = "AKIA_TEST_KEY"
        model.aws_secret_key = None
        model.aws_session_token = None
        model.aws_region = None

        client_params = model._get_client_params()

        # Target: aws_access_key should be present and set to the provided value
        self.assertIn('aws_access_key', client_params)
        self.assertEqual(client_params['aws_access_key'], "AKIA_TEST_KEY")

        # Other individual credentials that were not set should not be present
        self.assertNotIn('aws_secret_key', client_params)
        self.assertNotIn('aws_session_token', client_params)
        self.assertNotIn('aws_region', client_params)

        # max_retries is a class default (10) and should be present
        self.assertIn('max_retries', client_params)
        self.assertEqual(client_params['max_retries'], 10)
