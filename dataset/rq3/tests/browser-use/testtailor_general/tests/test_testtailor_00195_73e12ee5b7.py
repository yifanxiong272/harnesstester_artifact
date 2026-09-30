import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.deepseek.chat')
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
        """Verify that _client constructs AsyncOpenAI with provided params and client_params merged."""
        # Import the module that defines ChatDeepSeek using built-in __import__ to avoid needing sys
        module = __import__(ChatDeepSeek.__module__, fromlist=['*'])
        orig_async = getattr(module, 'AsyncOpenAI', None)

        class DummyAsyncOpenAI:
            def __init__(self, **kwargs):
                # store the constructor kwargs for assertions
                self._constructed_with = kwargs

        setattr(module, 'AsyncOpenAI', DummyAsyncOpenAI)
        try:
            # Instantiate ChatDeepSeek with explicit connection params and extra client_params
            cs = ChatDeepSeek(
                api_key='test-key-xyz',
                base_url='https://custom.deepseek.test/v1',
                timeout=7.5,
                client_params={'extra': 'value', 'retries': 2},
            )

            client = cs._client()

            # Ensure our dummy was used and received the expected parameters
            self.assertIsInstance(client, DummyAsyncOpenAI)
            constructed = client._constructed_with
            self.assertEqual(constructed.get('api_key'), 'test-key-xyz')
            self.assertEqual(constructed.get('base_url'), 'https://custom.deepseek.test/v1')
            self.assertEqual(constructed.get('timeout'), 7.5)
            # client_params should be merged into constructor kwargs
            self.assertIn('extra', constructed)
            self.assertEqual(constructed['extra'], 'value')
            self.assertIn('retries', constructed)
            self.assertEqual(constructed['retries'], 2)
        finally:
            # restore original AsyncOpenAI symbol
            if orig_async is not None:
                setattr(module, 'AsyncOpenAI', orig_async)
            else:
                if hasattr(module, 'AsyncOpenAI'):
                    delattr(module, 'AsyncOpenAI')
