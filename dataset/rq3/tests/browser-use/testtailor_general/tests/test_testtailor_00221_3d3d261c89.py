import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.cerebras.chat')
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
        """Ensure _client constructs AsyncOpenAI with passed parameters including client_params."""
        # Create a fake AsyncOpenAI to capture constructor kwargs
        class FakeAsyncOpenAI:
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

        # Replace the AsyncOpenAI reference in the module globals where ChatCerebras._client is defined
        globals_dict = ChatCerebras._client.__globals__
        original_async = globals_dict.get('AsyncOpenAI', None)
        globals_dict['AsyncOpenAI'] = FakeAsyncOpenAI

        try:
            # Instantiate ChatCerebras with specific connection parameters
            cc = ChatCerebras(
                api_key='test-key-123',
                base_url='https://example.test/v1',
                timeout=7.5,
                client_params={'custom': 'value', 'another': 42},
            )

            client = cc._client()

            # Verify we got back our fake and that it received the correct kwargs
            self.assertIsInstance(client, FakeAsyncOpenAI)
            self.assertEqual(client.kwargs.get('api_key'), 'test-key-123')
            self.assertEqual(client.kwargs.get('base_url'), 'https://example.test/v1')
            self.assertEqual(client.kwargs.get('timeout'), 7.5)
            # Ensure client_params were forwarded
            self.assertEqual(client.kwargs.get('custom'), 'value')
            self.assertEqual(client.kwargs.get('another'), 42)
        finally:
            # Restore original AsyncOpenAI reference
            if original_async is None:
                globals_dict.pop('AsyncOpenAI', None)
            else:
                globals_dict['AsyncOpenAI'] = original_async
