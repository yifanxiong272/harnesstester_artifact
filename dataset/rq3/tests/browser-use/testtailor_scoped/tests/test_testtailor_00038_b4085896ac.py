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
        # Case 1: some values are None and should be excluded; False should be included
        router1 = ChatOpenRouter(
            model='test-model-1',
            api_key='test-key',
            base_url='https://example.com',
            timeout=None,
            max_retries=3,
            default_headers=None,
            default_query={'q': 'v'},
            _strict_response_validation=False,  # should be included (not None)
            top_p=None,
            seed=None,
            http_client=None,
        )

        params1 = router1._get_client_params()
        expected1 = {
            'api_key': 'test-key',
            'base_url': 'https://example.com',
            'max_retries': 3,
            'default_query': {'q': 'v'},
            '_strict_response_validation': False,
        }
        self.assertEqual(params1, expected1)

        # Case 2: http_client provided should be added to the returned dict
        sentinel_client = object()
        router2 = ChatOpenRouter(
            model='test-model-2',
            api_key=None,
            base_url='https://openrouter.example',
            timeout=10,
            max_retries=10,
            default_headers={'X-Test': '1'},
            default_query=None,
            _strict_response_validation=False,
            top_p=0.9,
            seed=7,
            http_client=sentinel_client,
        )

        params2 = router2._get_client_params()
        expected2 = {
            'base_url': 'https://openrouter.example',
            'timeout': 10,
            'max_retries': 10,
            'default_headers': {'X-Test': '1'},
            '_strict_response_validation': False,
            'top_p': 0.9,
            'seed': 7,
            'http_client': sentinel_client,
        }
        self.assertEqual(params2, expected2)
