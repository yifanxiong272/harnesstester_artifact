import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.azure.chat')
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
        """Verify _get_client_params reads from environment, includes defaults, and respects explicit overrides."""
        # Backup existing environment vars to restore later
        old_key = os.environ.pop('AZURE_OPENAI_KEY', None)
        old_key2 = os.environ.pop('AZURE_OPENAI_API_KEY', None)
        old_endpoint = os.environ.pop('AZURE_OPENAI_ENDPOINT', None)
        old_deployment = os.environ.pop('AZURE_OPENAI_DEPLOYMENT', None)

        try:
            # Set environment variables that _get_client_params should pick up when instance values are None
            os.environ['AZURE_OPENAI_KEY'] = 'env_key_value'
            os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://env.azure.endpoint'
            os.environ['AZURE_OPENAI_DEPLOYMENT'] = 'env_deployment_value'

            # Create instance with None for the relevant fields so env vars get used
            llm = ChatAzureOpenAI(
                model='gpt-4o',
                api_key=None,
                azure_endpoint=None,
                azure_deployment=None,
            )

            # Provide default headers and query to exercise those branches
            llm.default_headers = {'X-Custom': 'hdr'}
            llm.default_query = {'param': 'value'}

            params = llm._get_client_params()

            # Environment values should be picked up
            self.assertIn('api_key', params)
            self.assertEqual(params['api_key'], 'env_key_value')

            self.assertIn('azure_endpoint', params)
            self.assertEqual(params['azure_endpoint'], 'https://env.azure.endpoint')

            self.assertIn('azure_deployment', params)
            self.assertEqual(params['azure_deployment'], 'env_deployment_value')

            # api_version has a default and should be present
            self.assertIn('api_version', params)
            self.assertEqual(params['api_version'], llm.api_version)

            # default headers and query should be present because we set them
            self.assertIn('default_headers', params)
            self.assertEqual(params['default_headers'], {'X-Custom': 'hdr'})
            self.assertIn('default_query', params)
            self.assertEqual(params['default_query'], {'param': 'value'})

            # Fields that remain None should not be included
            self.assertNotIn('azure_ad_token', params)
            self.assertNotIn('azure_ad_token_provider', params)
            self.assertNotIn('base_url', params)
            # http_client defaults to None on the instance so it shouldn't be present
            self.assertNotIn('http_client', params)

            # Now verify explicit instance value overrides environment
            llm.api_key = 'explicit_key'
            params2 = llm._get_client_params()
            self.assertEqual(params2['api_key'], 'explicit_key')

        finally:
            # Restore environment
            if old_key is not None:
                os.environ['AZURE_OPENAI_KEY'] = old_key
            else:
                os.environ.pop('AZURE_OPENAI_KEY', None)

            if old_key2 is not None:
                os.environ['AZURE_OPENAI_API_KEY'] = old_key2
            else:
                os.environ.pop('AZURE_OPENAI_API_KEY', None)

            if old_endpoint is not None:
                os.environ['AZURE_OPENAI_ENDPOINT'] = old_endpoint
            else:
                os.environ.pop('AZURE_OPENAI_ENDPOINT', None)

            if old_deployment is not None:
                os.environ['AZURE_OPENAI_DEPLOYMENT'] = old_deployment
            else:
                os.environ.pop('AZURE_OPENAI_DEPLOYMENT', None)
