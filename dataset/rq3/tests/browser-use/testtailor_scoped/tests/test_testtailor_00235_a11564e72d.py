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
        """When no session is provided but aws_secret_key is set, it should appear in client params."""
        # Create instance without a session and with only aws_secret_key set
        model = ChatAnthropicBedrock(aws_secret_key="s3cr3t_value")
        # Ensure session is not set to follow the branch
        self.assertIsNone(model.session)
        client_params = model._get_client_params()
        # The aws_secret_key must be present and equal to the provided value
        self.assertIn('aws_secret_key', client_params)
        self.assertEqual(client_params['aws_secret_key'], "s3cr3t_value")
