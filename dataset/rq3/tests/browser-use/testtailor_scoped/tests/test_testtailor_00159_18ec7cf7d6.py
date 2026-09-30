import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.ollama.chat')
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
        """Ensure get_client constructs OllamaAsyncClient with provided host, timeout and client_params."""
        import sys
        from unittest import mock

        # Prepare a fake OllamaAsyncClient to capture initialization parameters
        init_args = {}

        class FakeOllamaAsyncClient:
            def __init__(self, host=None, timeout=None, **kwargs):
                init_args['host'] = host
                init_args['timeout'] = timeout
                init_args['kwargs'] = kwargs

        # Patch the OllamaAsyncClient symbol in the module where ChatOllama is defined
        module = sys.modules[ChatOllama.__module__]
        with mock.patch.object(module, "OllamaAsyncClient", new=FakeOllamaAsyncClient):
            # Create ChatOllama with explicit host, timeout and client_params
            chat = ChatOllama(model="test-model", host="http://example.local", timeout=2.5, client_params={"foo": "bar"})
            client = chat.get_client()

        # Verify that the patched FakeOllamaAsyncClient was used and received correct args
        self.assertIsInstance(client, FakeOllamaAsyncClient)
        self.assertEqual(init_args["host"], "http://example.local")
        self.assertEqual(init_args["timeout"], 2.5)
        self.assertEqual(init_args["kwargs"], {"foo": "bar"})
