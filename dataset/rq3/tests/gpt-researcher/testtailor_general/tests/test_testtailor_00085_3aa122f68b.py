import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.retrievers.utils')
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
        """Test stream_output sends JSON including data when with_data is True and websocket provided."""
        async def run():
            # Create a simple websocket-like object with an async send_json method that records the payload
            ws = type("WS", (), {})()
            ws.sent = None

            async def send_json(payload):
                ws.sent = payload

            ws.send_json = send_json

            # Call the function under test with with_data=True so the branch including "data" is executed
            await stream_output("info", "step1", "the content", websocket=ws, with_data=True, data={"key": "value"})

            # Verify the payload sent to websocket includes the "data" key
            expected = {
                "type": "info",
                "step": "step1",
                "content": "the content",
                "data": {"key": "value"}
            }
            self.assertEqual(ws.sent, expected)

        asyncio = __import__('asyncio')
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run())
        finally:
            loop.close()
