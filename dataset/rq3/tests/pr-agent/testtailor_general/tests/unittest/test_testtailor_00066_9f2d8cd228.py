import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.secret_providers.aws_secrets_manager_provider')
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
        """Ensure boto3.client is called without region_name when no region is configured"""
        with patch('pr_agent.secret_providers.aws_secrets_manager_provider.get_settings') as mock_get_settings, \
             patch('pr_agent.secret_providers.aws_secrets_manager_provider.boto3.client') as mock_boto3_client:

            settings = MagicMock()
            # No region values, but secret ARN is present
            def _get(key, default=None):
                return {
                    'aws_secrets_manager.secret_arn': 'arn:aws:secretsmanager:us-east-1:123:secret:test'
                }.get(key, default)
            settings.get.side_effect = _get
            mock_get_settings.return_value = settings

            mock_client = MagicMock()
            mock_boto3_client.return_value = mock_client

            provider = AWSSecretsManagerProvider()

            # boto3.client should be called without region_name argument
            mock_boto3_client.assert_called_once_with('secretsmanager')
            self.assertIs(provider.client, mock_client)
            self.assertEqual(provider.secret_arn, 'arn:aws:secretsmanager:us-east-1:123:secret:test')
