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
        """Ensure that when session is provided, credentials and region are taken from the session."""
        # Create dummy credentials and session objects that mimic the expected interface
        class DummyCredentials:
            def __init__(self, access_key, secret_key, token):
                self.access_key = access_key
                self.secret_key = secret_key
                self.token = token

        class DummySession:
            def __init__(self, region_name, credentials):
                self.region_name = region_name
                self._credentials = credentials

            def get_credentials(self):
                return self._credentials

        creds = DummyCredentials("AKIA_TEST_KEY", "SECRET_TEST_KEY", "SESSION_TOKEN_123")
        session = DummySession("us-west-2", creds)

        # Instantiate the model and assign the session
        model = ChatAnthropicBedrock()
        model.session = session

        # Call the method under test
        client_params = model._get_client_params()

        # Expected parameters should come from the session credentials and region,
        # and include default max_retries since it's truthy (10).
        expected = {
            "aws_access_key": "AKIA_TEST_KEY",
            "aws_secret_key": "SECRET_TEST_KEY",
            "aws_session_token": "SESSION_TOKEN_123",
            "aws_region": "us-west-2",
            "max_retries": 10,
        }

        self.assertEqual(client_params, expected)
