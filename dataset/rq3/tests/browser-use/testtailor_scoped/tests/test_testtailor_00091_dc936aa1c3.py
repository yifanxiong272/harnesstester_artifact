import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.browser_use.chat')
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
        """Ensure session_id from kwargs is added to payload and sent to _make_request."""
        client = ChatBrowserUse(api_key='test-key', model='bu-2-0')

        # Minimal dummy message that satisfies _serialize_message (expects model_dump())
        class DummyMessage:
            def model_dump(self):
                return {'role': 'user', 'content': 'hello'}

        dummy = DummyMessage()

        async def fake_make_request(payload):
            # The target line should have run, so session_id must be present in payload
            assert payload.get('session_id') == 'session-123'
            # Basic sanity checks on payload
            assert payload['model'] == client.model
            assert isinstance(payload['messages'], list)
            # Return a minimal successful response
            return {'completion': 'ok', 'usage': None}

        # Patch the client's _make_request to our fake implementation
        client._make_request = fake_make_request

        # Call the async method and verify the returned completion
        result = asyncio.run(client.ainvoke([dummy], request_type='browser_agent', session_id='session-123'))
        self.assertIsInstance(result, ChatInvokeCompletion)
        self.assertEqual(result.completion, 'ok')
