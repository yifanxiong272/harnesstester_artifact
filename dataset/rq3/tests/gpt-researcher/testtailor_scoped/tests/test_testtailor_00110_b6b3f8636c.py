import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.actions.utils')
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
        """Verify that when a websocket is provided, send_json is awaited with correct payload."""
        # create a fake websocket with an async send_json method that records the data it receives
        class FakeWebSocket:
            def __init__(self):
                self.sent = None

            async def send_json(self, data):
                # record the payload for assertions
                self.sent = data

        websocket = FakeWebSocket()
        # prepare inputs
        msg_type = "text"
        content = "hello"
        output = "world"
        metadata = {"key": "value"}

        # obtain asyncio module without using an import statement at the top level
        _asyncio = __import__("asyncio")

        # call the async function, handling running event loop if necessary
        coro = stream_output(msg_type, content, output, websocket=websocket, output_log=True, metadata=metadata)

        loop = _asyncio.get_event_loop()
        if loop.is_running():
            # If the current loop is running (e.g., in some test runners), create a new loop to run the coroutine
            new_loop = _asyncio.new_event_loop()
            try:
                new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
        else:
            loop.run_until_complete(coro)

        # assert that the websocket's send_json was called with the expected payload
        expected = {"type": msg_type, "content": content, "output": output, "metadata": metadata}
        self.assertEqual(websocket.sent, expected)
