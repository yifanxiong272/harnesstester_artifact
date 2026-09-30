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
        """Test that a simple 'chat' message string is parsed, converted to messages,
        handled by ChatAgentWithMemory, and the websocket receives the assistant response."""
        # Dummy websocket to capture sent JSON
        class DummyWebSocket:
            def __init__(self):
                self.sent = []
            async def send_json(self, obj):
                self.sent.append(obj)

        ws = DummyWebSocket()

        # Capture data passed into the dummy agent
        captured = {}

        # Dummy ChatAgentWithMemory to be injected into the handler's globals
        class DummyAgent:
            def __init__(self, report, config_path, headers):
                captured['report'] = report
                captured['config_path'] = config_path
                captured['headers'] = headers
            async def chat(self, messages, websocket):
                captured['messages'] = messages
                captured['websocket'] = websocket
                # Return a reply and some tool-call metadata
                return "ok-reply", [{"tool": "t1"}]

        # Inject dummy agent into the function's globals so handle_chat_command will use it
        handle_chat_command.__globals__['ChatAgentWithMemory'] = DummyAgent

        # Prepare input data: use a JSON string with only "message" so code converts to messages format
        data = 'chat {"message": "Hi there"}'

        # Run the async handler
        loop = asyncio.get_event_loop()
        loop.run_until_complete(handle_chat_command(ws, data))

        # Verify websocket received a response
        self.assertTrue(ws.sent, "No message was sent on the websocket")
        expected = {
            "type": "chat",
            "content": "ok-reply",
            "role": "assistant",
            "metadata": {"tool_calls": [{"tool": "t1"}]}
        }
        self.assertEqual(ws.sent[-1], expected)

        # Verify the agent saw the converted messages and report
        self.assertEqual(captured.get('messages'), [{"role": "user", "content": "Hi there"}])
        self.assertEqual(captured.get('report'), "")
