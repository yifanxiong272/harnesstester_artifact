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
        async def runner():
            class DummyWebsocket:
                def __init__(self):
                    self.called = False
                    self.payload = None

                async def send_json(self, payload):
                    self.called = True
                    self.payload = payload

            ws = DummyWebsocket()
            # Call the function under test with websocket present and with_data False
            await stream_output("info", "step1", "hello", websocket=ws, with_data=False, data={"ignored": True})

            # Verify send_json was called and the payload does not include "data"
            self.assertTrue(ws.called)
            self.assertEqual(ws.payload, {
                "type": "info",
                "step": "step1",
                "content": "hello"
            })

        __import__('asyncio').run(runner())
