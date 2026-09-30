import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.openrouter.chat')
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
        """Verify _get_client_params filters out None values and includes http_client when present."""
        # Fully populated client params
        router = ChatOpenRouter(
            model='test-model',
            api_key='test-key',
            base_url='https://example.com/api',
            timeout=5.0,
            max_retries=3,
            default_headers={'X-Test': '1'},
            default_query={'debug': True},
            top_p=0.8,
            seed=123,
        )

        params = router._get_client_params()

        # All explicitly set, non-None values should be present
        self.assertEqual(params['api_key'], 'test-key')
        self.assertEqual(params['base_url'], 'https://example.com/api')
        self.assertEqual(params['timeout'], 5.0)
        self.assertEqual(params['max_retries'], 3)
        self.assertEqual(params['default_headers'], {'X-Test': '1'})
        self.assertEqual(params['default_query'], {'debug': True})
        self.assertEqual(params['top_p'], 0.8)
        self.assertEqual(params['seed'], 123)
        # _strict_response_validation has a default (False) and should be present (not filtered out)
        self.assertIn('_strict_response_validation', params)

        # Now test with several None values and a provided http_client
        fake_http_client = object()
        router2 = ChatOpenRouter(
            model='test-model-2',
            api_key='key2',
            base_url='https://example.org',
            timeout=None,
            default_headers=None,
            default_query=None,
            top_p=None,
            seed=None,
            http_client=fake_http_client,
        )

        params2 = router2._get_client_params()

        # Provided http_client should be included
        self.assertIn('http_client', params2)
        self.assertIs(params2['http_client'], fake_http_client)

        # Keys that were explicitly set to None should not appear
        self.assertNotIn('timeout', params2)
        self.assertNotIn('default_headers', params2)
        self.assertNotIn('default_query', params2)
        self.assertNotIn('top_p', params2)
        self.assertNotIn('seed', params2)

        # Required non-None defaults or provided values should remain
        self.assertEqual(params2['api_key'], 'key2')
        self.assertEqual(params2['base_url'], 'https://example.org')
        self.assertIn('max_retries', params2)
        self.assertIn('_strict_response_validation', params2)
