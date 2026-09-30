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
        """Ensure get_client constructs AsyncOpenAI when _client is not present and caches it."""
        # Create a ChatOpenRouter instance with minimal required fields
        router = ChatOpenRouter(model='test-model', api_key='test-key')

        # Verify no _client attribute initially
        self.assertFalse(hasattr(router, '_client'))

        # Patch the AsyncOpenAI class used inside the ChatOpenRouter module
        with unittest.mock.patch('browser_use.llm.openrouter.chat.AsyncOpenAI') as mock_async_openai_cls:
            # Configure the mock to return a sentinel object for easy identity checks
            sentinel_client = object()
            mock_async_openai_cls.return_value = sentinel_client

            # Compute expected client params from the instance (what _get_client_params would return)
            expected_params = router._get_client_params()

            # Call get_client which should create and return the mocked AsyncOpenAI instance
            client = router.get_client()

            # Verify the returned client is the sentinel object from the mock
            self.assertIs(client, sentinel_client)

            # Ensure AsyncOpenAI was constructed exactly once with the expected parameters
            mock_async_openai_cls.assert_called_once_with(**expected_params)

            # Calling get_client again should return the same cached client and not call the constructor again
            client_again = router.get_client()
            self.assertIs(client_again, sentinel_client)
            self.assertEqual(mock_async_openai_cls.call_count, 1)
