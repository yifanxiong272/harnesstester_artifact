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
        """Verify that _client constructs AsyncOpenAI with the expected parameters."""
        # Get the module where ChatCerebras is defined without using importlib
        mod = __import__(ChatCerebras.__module__, fromlist=['*'])

        captured = {}

        class DummyAsyncOpenAI:
            def __init__(self, api_key=None, base_url=None, timeout=None, **kwargs):
                # capture init args for assertions
                captured['api_key'] = api_key
                captured['base_url'] = base_url
                captured['timeout'] = timeout
                captured['extra_kwargs'] = kwargs

            def __repr__(self):
                return "<DummyAsyncOpenAI>"

        # Patch the AsyncOpenAI used by ChatCerebras to our dummy
        with unittest.mock.patch.object(mod, 'AsyncOpenAI', DummyAsyncOpenAI):
            cfg = {
                'api_key': 'test-key-xyz',
                'base_url': 'https://example-cerebras.test/v1',
                'timeout': 7.5,
                'client_params': {'custom': 'value', 'n': 1},
            }
            model = ChatCerebras(
                model='llama3.1-8b-test',
                api_key=cfg['api_key'],
                base_url=cfg['base_url'],
                timeout=cfg['timeout'],
                client_params=cfg['client_params'],
            )

            client = model._client()

        # Assertions: ensure our dummy was constructed and received the right args
        self.assertIsInstance(client, DummyAsyncOpenAI)
        self.assertEqual(captured['api_key'], cfg['api_key'])
        self.assertEqual(captured['base_url'], cfg['base_url'])
        self.assertEqual(captured['timeout'], cfg['timeout'])
        self.assertEqual(captured['extra_kwargs'], cfg['client_params'])
