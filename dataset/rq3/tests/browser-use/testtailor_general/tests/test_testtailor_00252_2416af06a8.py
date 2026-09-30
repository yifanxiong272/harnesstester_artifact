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
        """Ensure session_id is added to the payload and sent to _make_request."""
        client = ChatBrowserUse(api_key='test-key')

        # Simple message class that matches what _serialize_message expects
        class SimpleMessage:
            def __init__(self, role: str, content: str):
                self._d = {'role': role, 'content': content}

            def model_dump(self):
                return self._d

        captured = {}

        async def fake_make_request(payload):
            # Capture the payload passed in and return a minimal valid response
            captured['payload'] = payload
            return {'completion': 'ok', 'usage': None}

        # Replace the instance method with our fake async function
        client._make_request = fake_make_request

        messages = [SimpleMessage('user', 'hello')]
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(client.ainvoke(messages, session_id='sess-123'))

        # Verify session_id was included in the payload and the completion was returned
        self.assertIn('session_id', captured['payload'])
        self.assertEqual(captured['payload']['session_id'], 'sess-123')
        self.assertEqual(result.completion, 'ok')
