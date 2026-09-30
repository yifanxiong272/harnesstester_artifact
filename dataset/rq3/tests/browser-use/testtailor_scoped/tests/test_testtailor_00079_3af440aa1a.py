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
        """Verify _get_client_params picks up env vars, includes defaults and omits None values."""
        # Save existing environment variables to restore later
        env_keys = ['AZURE_OPENAI_KEY', 'AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_DEPLOYMENT']
        old_env = {k: os.environ.get(k) for k in env_keys}
        try:
            # Ensure AZURE_OPENAI_KEY is not set so fallback to AZURE_OPENAI_API_KEY is tested
            if 'AZURE_OPENAI_KEY' in os.environ:
                del os.environ['AZURE_OPENAI_KEY']
            os.environ['AZURE_OPENAI_API_KEY'] = 'env_api_key_value'
            os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://example.azure.endpoint'
            os.environ['AZURE_OPENAI_DEPLOYMENT'] = 'env-deployment-42'

            # Create ChatAzureOpenAI with None values so env vars are used
            llm = ChatAzureOpenAI(model='test-model', api_key=None, azure_endpoint=None, azure_deployment=None)

            # Set some instance-level optional params to ensure they're propagated
            llm.default_headers = {'X-Test-Header': 'value'}
            llm.default_query = {'debug': True}
            sentinel_http_client = object()
            llm.http_client = sentinel_http_client

            params = llm._get_client_params()

            # api_key should be picked up from AZURE_OPENAI_API_KEY (since AZURE_OPENAI_KEY unset)
            self.assertIn('api_key', params)
            self.assertEqual(params['api_key'], 'env_api_key_value')

            # azure endpoint & deployment should be picked up from environment
            self.assertEqual(params.get('azure_endpoint'), 'https://example.azure.endpoint')
            self.assertEqual(params.get('azure_deployment'), 'env-deployment-42')

            # api_version should be present (class default)
            self.assertIn('api_version', params)
            self.assertEqual(params['api_version'], llm.api_version)

            # default_headers and default_query should be included when set
            self.assertIn('default_headers', params)
            self.assertEqual(params['default_headers'], {'X-Test-Header': 'value'})
            self.assertIn('default_query', params)
            self.assertEqual(params['default_query'], {'debug': True})

            # http_client should be included and be the sentinel we set
            self.assertIn('http_client', params)
            self.assertIs(params['http_client'], sentinel_http_client)

            # base_url and organization were not set on the instance, so they should not appear
            self.assertNotIn('base_url', params)
            self.assertNotIn('organization', params)

        finally:
            # Restore environment
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
