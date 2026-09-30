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
        """Ensure get_client constructs AsyncOpenAI with _get_client_params and caches it."""
        # Patch AsyncOpenAI in the module where ChatVercel is defined to a fake class
        mod = __import__(ChatVercel.__module__, fromlist=['*'])
        orig_async = getattr(mod, 'AsyncOpenAI', None)

        class FakeAsyncOpenAI:
            def __init__(self, **kwargs):
                # record received initialization kwargs for assertions
                self._init_kwargs = kwargs

        try:
            setattr(mod, 'AsyncOpenAI', FakeAsyncOpenAI)

            # Create an instance with explicit client params so _get_client_params returns them
            llm = ChatVercel(
                model='openai/gpt-test',
                api_key='test-key',
                base_url='https://ai-gateway.vercel.sh/v1',
                timeout=2.5,
                max_retries=4,
                default_headers={'x-test': '1'},
                default_query={'q': 'v'},
                _strict_response_validation=True,
            )

            # Ensure no client exists yet
            self.assertFalse(hasattr(llm, '_client'))

            # Call get_client which should construct FakeAsyncOpenAI with the client params
            client = llm.get_client()

            # The returned client should be an instance of our fake class
            self.assertIsInstance(client, FakeAsyncOpenAI)

            # Expected parameters constructed by _get_client_params (only non-None keys)
            expected_params = {
                'api_key': 'test-key',
                'base_url': 'https://ai-gateway.vercel.sh/v1',
                'timeout': 2.5,
                'max_retries': 4,
                'default_headers': {'x-test': '1'},
                'default_query': {'q': 'v'},
                '_strict_response_validation': True,
            }

            self.assertEqual(client._init_kwargs, expected_params)

            # Subsequent calls should return the same cached client
            self.assertTrue(hasattr(llm, '_client'))
            self.assertIs(llm.get_client(), client)

        finally:
            # Restore original AsyncOpenAI symbol
            if orig_async is None:
                try:
                    delattr(mod, 'AsyncOpenAI')
                except Exception:
                    pass
            else:
                setattr(mod, 'AsyncOpenAI', orig_async)
