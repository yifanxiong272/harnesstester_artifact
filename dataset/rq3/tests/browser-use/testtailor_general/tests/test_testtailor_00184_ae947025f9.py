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
        """Ensure _get_client_params builds params when a session with credentials is present."""
        # Create dummy credentials and session objects to simulate boto3-like session
        class DummyCredentials:
            def __init__(self):
                self.access_key = "AKIA_TEST"
                self.secret_key = "SECRET_TEST"
                self.token = "SESSION_TOKEN_TEST"

        class DummySession:
            def __init__(self):
                self.region_name = "us-west-2"

            def get_credentials(self):
                return DummyCredentials()

        # Instantiate the model and attach the dummy session
        model = ChatAnthropicBedrock()
        model.session = DummySession()

        # Call the method under test
        client_params = model._get_client_params()

        # Expected params should include credentials from the session and the default max_retries
        expected = {
            "aws_access_key": "AKIA_TEST",
            "aws_secret_key": "SECRET_TEST",
            "aws_session_token": "SESSION_TOKEN_TEST",
            "aws_region": "us-west-2",
            "max_retries": model.max_retries,
        }

        self.assertEqual(client_params, expected)
