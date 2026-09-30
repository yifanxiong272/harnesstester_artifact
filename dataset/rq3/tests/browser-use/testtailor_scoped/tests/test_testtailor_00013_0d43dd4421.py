import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.openai.chat')
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
        """Ensure _get_client_params filters out None values and includes http_client when provided."""
        # Create a ChatOpenAI instance and set attributes explicitly to avoid depending
        # on constructor signature.
        chat = ChatOpenAI(model='test-model')
        chat.api_key = 'my-api-key'
        chat.organization = None  # should be filtered out
        chat.project = 'my-project'
        chat.base_url = 'https://api.example'
        chat.websocket_base_url = None  # should be filtered out
        chat.timeout = 10
        chat.max_retries = 3
        chat.default_headers = {'X-Test': 'yes'}
        chat.default_query = None  # should be filtered out
        chat._strict_response_validation = False  # False is not None and should be included
        sentinel_http_client = object()
        chat.http_client = sentinel_http_client

        params = chat._get_client_params()

        # Keys that were explicitly set to non-None must be present
        self.assertIn('api_key', params)
        self.assertEqual(params['api_key'], 'my-api-key')

        self.assertIn('project', params)
        self.assertEqual(params['project'], 'my-project')

        self.assertIn('base_url', params)
        self.assertEqual(params['base_url'], 'https://api.example')

        self.assertIn('timeout', params)
        self.assertEqual(params['timeout'], 10)

        self.assertIn('max_retries', params)
        self.assertEqual(params['max_retries'], 3)

        self.assertIn('default_headers', params)
        self.assertEqual(params['default_headers'], {'X-Test': 'yes'})

        # _strict_response_validation set to False should still be present (not filtered as None)
        self.assertIn('_strict_response_validation', params)
        self.assertFalse(params['_strict_response_validation'])

        # Keys set to None must be absent
        self.assertNotIn('organization', params)
        self.assertNotIn('websocket_base_url', params)
        self.assertNotIn('default_query', params)

        # http_client should be added when provided
        self.assertIn('http_client', params)
        self.assertIs(params['http_client'], sentinel_http_client)
