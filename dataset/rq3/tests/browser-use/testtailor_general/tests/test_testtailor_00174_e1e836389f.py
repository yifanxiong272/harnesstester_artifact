import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.anthropic.chat')
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
        """Ensure _get_client_params only includes non-None values (explicitly set timeout to None)."""
        # Create model with default values; timeout defaults to NotGiven() sentinel at class definition.
        model = ChatAnthropic(model='claude-test')

        # Set some attributes to concrete values and leave others as None / NotGiven
        model.api_key = 'test-key'
        model.auth_token = None  # should be excluded
        model.base_url = 'https://api.example.com'
        # Explicitly set timeout to None so it is excluded from client_params
        model.timeout = None
        model.max_retries = 5
        model.default_headers = {'X-Test': '1'}
        model.default_query = None  # should be excluded
        model.http_client = None  # should be excluded

        client_params = model._get_client_params()

        # Expected keys: api_key, base_url, max_retries, default_headers
        expected_keys = {'api_key', 'base_url', 'max_retries', 'default_headers'}
        self.assertEqual(set(client_params.keys()), expected_keys)

        # Validate values
        self.assertEqual(client_params['api_key'], 'test-key')
        self.assertEqual(client_params['base_url'], 'https://api.example.com')
        self.assertEqual(client_params['max_retries'], 5)
        self.assertEqual(client_params['default_headers'], {'X-Test': '1'})
