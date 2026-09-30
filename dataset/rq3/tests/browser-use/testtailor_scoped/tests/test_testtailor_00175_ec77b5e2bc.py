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
        """Ensure get_client constructs AsyncOpenAI with the expected client params."""
        # Prepare a ChatOpenAI instance with a variety of client params set.
        svc_model = "o1"
        hc = object()
        chat = ChatOpenAI(
            model=svc_model,
            api_key="test-key",
            organization="test-org",
            project="test-proj",
            base_url="https://api.example",
            websocket_base_url="wss://ws.example",
            timeout=5,
            max_retries=9,
            default_headers={"h": "v"},
            default_query={"q": 1},
            http_client=hc,
            _strict_response_validation=True,
        )

        # Capture the constructor kwargs passed to AsyncOpenAI by temporarily
        # replacing the symbol in the ChatOpenAI defining module.
        module = __import__(ChatOpenAI.__module__, fromlist=['*'])
        captured = {}

        class DummyAsyncOpenAI:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        with unittest.mock.patch.object(module, "AsyncOpenAI", DummyAsyncOpenAI):
            client = chat.get_client()

        # The returned object should be an instance of our dummy replacement.
        self.assertIsInstance(client, DummyAsyncOpenAI)

        # Expected params: only non-None fields from _get_client_params plus http_client.
        expected = {
            "api_key": "test-key",
            "organization": "test-org",
            "project": "test-proj",
            "base_url": "https://api.example",
            "websocket_base_url": "wss://ws.example",
            "timeout": 5,
            "max_retries": 9,
            "default_headers": {"h": "v"},
            "default_query": {"q": 1},
            "_strict_response_validation": True,
            "http_client": hc,
        }

        self.assertDictEqual(captured, expected)
