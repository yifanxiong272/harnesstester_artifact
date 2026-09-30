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
        """Ensure _get_client_params picks up env var when api_key is None,
        filters out None values, and includes http_client when provided.
        Also ensure an explicit api_key on the instance overrides env vars.
        """
        # Preserve environment
        old_ai_key = os.environ.get('AI_GATEWAY_API_KEY')
        old_vercel = os.environ.get('VERCEL_OIDC_TOKEN')
        try:
            # Set only AI_GATEWAY_API_KEY to exercise fallback selection
            os.environ['AI_GATEWAY_API_KEY'] = 'env_api_key_value'
            if 'VERCEL_OIDC_TOKEN' in os.environ:
                del os.environ['VERCEL_OIDC_TOKEN']

            dummy_http_client = object()

            # Create instance with api_key=None so env var should be used
            inst = ChatVercel(
                model='test-model',
                api_key=None,
                base_url='https://custom.example',
                timeout=None,  # should be filtered out
                max_retries=7,
                default_headers=None,  # should be filtered out
                default_query=None,    # should be filtered out
                http_client=dummy_http_client,
                _strict_response_validation=False,
            )

            params = inst._get_client_params()

            # api_key should come from environment
            self.assertIn('api_key', params)
            self.assertEqual(params['api_key'], 'env_api_key_value')

            # None-valued entries should be removed
            self.assertNotIn('timeout', params)
            self.assertNotIn('default_headers', params)
            self.assertNotIn('default_query', params)

            # Provided non-None entries should be present and correct
            self.assertEqual(params['base_url'], 'https://custom.example')
            self.assertEqual(params['max_retries'], 7)
            self.assertIn('_strict_response_validation', params)
            self.assertIs(params['_strict_response_validation'], False)

            # http_client should be included when not None
            self.assertIn('http_client', params)
            self.assertIs(params['http_client'], dummy_http_client)

            # Now ensure explicit api_key on the instance overrides the env var
            inst2 = ChatVercel(model='m2', api_key='explicit_key')
            params2 = inst2._get_client_params()
            self.assertEqual(params2.get('api_key'), 'explicit_key')

        finally:
            # Restore environment
            if old_ai_key is None:
                os.environ.pop('AI_GATEWAY_API_KEY', None)
            else:
                os.environ['AI_GATEWAY_API_KEY'] = old_ai_key

            if old_vercel is None:
                os.environ.pop('VERCEL_OIDC_TOKEN', None)
            else:
                os.environ['VERCEL_OIDC_TOKEN'] = old_vercel
