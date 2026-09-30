import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.vercel.chat')
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
        """Test _get_client_params uses env var for api_key, filters out None values,
        includes False boolean, and attaches http_client when provided."""
        # Preserve environment
        prev_ai_key = os.environ.get('AI_GATEWAY_API_KEY')
        prev_vercel = os.environ.get('VERCEL_OIDC_TOKEN')
        try:
            # Ensure VERCEL_OIDC_TOKEN is not set so AI_GATEWAY_API_KEY is used
            os.environ.pop('VERCEL_OIDC_TOKEN', None)
            os.environ['AI_GATEWAY_API_KEY'] = 'env-123'

            dummy_http = object()
            # Create instance with a mix of None and non-None fields
            llm = ChatVercel(
                model='openai/gpt-test',
                api_key=None,  # should fall back to env var
                timeout=2.5,
                max_retries=3,
                default_headers={'x': 'y'},
                default_query=None,  # should be filtered out
                http_client=dummy_http,
            )

            params = llm._get_client_params()

            # api_key should come from environment
            self.assertEqual(params['api_key'], 'env-123')
            # base_url present and equals instance value
            self.assertEqual(params['base_url'], llm.base_url)
            # timeout and max_retries preserved
            self.assertEqual(params['timeout'], 2.5)
            self.assertEqual(params['max_retries'], 3)
            # default_headers included, default_query omitted because it's None
            self.assertEqual(params['default_headers'], {'x': 'y'})
            self.assertNotIn('default_query', params)
            # _strict_response_validation is a boolean defaulting to False and should be included
            self.assertIn('_strict_response_validation', params)
            self.assertFalse(params['_strict_response_validation'])
            # http_client should be attached when provided
            self.assertIs(params['http_client'], dummy_http)

        finally:
            # Restore environment
            if prev_ai_key is None:
                os.environ.pop('AI_GATEWAY_API_KEY', None)
            else:
                os.environ['AI_GATEWAY_API_KEY'] = prev_ai_key

            if prev_vercel is None:
                os.environ.pop('VERCEL_OIDC_TOKEN', None)
            else:
                os.environ['VERCEL_OIDC_TOKEN'] = prev_vercel
