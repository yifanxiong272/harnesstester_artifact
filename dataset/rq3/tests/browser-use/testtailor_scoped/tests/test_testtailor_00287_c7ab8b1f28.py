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
        """Ensure aws_region is added to client params when session is not provided."""
        # Create instance without a session but with aws_region set
        bedrock = ChatAnthropicBedrock(aws_region='us-west-2')

        # Sanity check: session should be falsy to follow the intended branch
        self.assertFalse(bedrock.session)

        client_params = bedrock._get_client_params()

        # The aws_region key must be present and set to the provided value
        self.assertIn('aws_region', client_params)
        self.assertEqual(client_params['aws_region'], 'us-west-2')

        # Ensure other credential keys are not present since they were not provided
        self.assertNotIn('aws_access_key', client_params)
        self.assertNotIn('aws_secret_key', client_params)
        # max_retries has a default truthy value and should be included
        self.assertIn('max_retries', client_params)
        self.assertEqual(client_params['max_retries'], bedrock.max_retries)
