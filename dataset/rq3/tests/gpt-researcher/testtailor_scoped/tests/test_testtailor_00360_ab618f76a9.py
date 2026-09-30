import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('backend.server.server_utils')
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
        """When no message or messages are provided the handler should notify via websocket."""
        # Dummy websocket to capture send_json calls
        class DummyWebSocket:
            def __init__(self):
                self.sent = None

            async def send_json(self, obj):
                self.sent = obj

        ws = DummyWebSocket()
        # Provide data with the "chat " prefix but no message or messages content
        data = 'chat {}'

        # Run the async handler
        asyncio.run(handle_chat_command(ws, data))

        # Verify the websocket received the expected "No message provided." response
        self.assertIsNotNone(ws.sent)
        expected = {
            "type": "chat",
            "content": "No message provided.",
            "role": "assistant"
        }
        self.assertEqual(ws.sent, expected)
