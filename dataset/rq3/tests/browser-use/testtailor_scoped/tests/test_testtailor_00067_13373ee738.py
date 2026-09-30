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
        """Ensure ChatDeepSeek._client instantiates AsyncOpenAI with expected arguments."""
        # Capture init args in a dict
        init_calls = {}

        class DummyAsyncOpenAI:
            def __init__(self, api_key=None, base_url=None, timeout=None, **kwargs):
                init_calls['api_key'] = api_key
                init_calls['base_url'] = base_url
                init_calls['timeout'] = timeout
                init_calls['kwargs'] = kwargs

        # Patch the AsyncOpenAI symbol used inside ChatDeepSeek._client by modifying the function globals
        func_globals = ChatDeepSeek._client.__globals__
        original_async_openai = func_globals.get('AsyncOpenAI')
        func_globals['AsyncOpenAI'] = DummyAsyncOpenAI

        try:
            cs = ChatDeepSeek(
                api_key='test-key',
                base_url='https://api.test.com/v1',
                timeout=3.5,
                client_params={'extra': 'value'},
            )
            client = cs._client()

            # Verify that our dummy was instantiated and received the expected parameters
            self.assertIsInstance(client, DummyAsyncOpenAI)
            self.assertEqual(init_calls['api_key'], 'test-key')
            self.assertEqual(str(init_calls['base_url']), 'https://api.test.com/v1')
            self.assertEqual(init_calls['timeout'], 3.5)
            self.assertEqual(init_calls['kwargs'], {'extra': 'value'})
        finally:
            # Restore original symbol to avoid side effects
            if original_async_openai is not None:
                func_globals['AsyncOpenAI'] = original_async_openai
            else:
                del func_globals['AsyncOpenAI']
