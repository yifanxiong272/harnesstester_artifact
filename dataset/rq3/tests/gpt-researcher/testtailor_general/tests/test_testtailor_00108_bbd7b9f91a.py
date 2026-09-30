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
        async def run():
            # Dummy websocket that would record any sends (should not be called)
            class DummyWebSocket:
                def __init__(self):
                    self.sent = None
                async def send_json(self, data):
                    self.sent = data

            ws = DummyWebSocket()

            # Manager whose start_streaming should NOT be called; if it is, fail the test
            class DummyManager:
                async def start_streaming(self, *args, **kwargs):
                    raise AssertionError("start_streaming should not be called when task or report_type is missing")

            manager = DummyManager()

            # Build data with missing/empty task to trigger the early return
            data = 'START {"task": "", "report_type": null}'

            # Call the handler; it should return early and not use websocket or manager
            await handle_start_command(ws, data, manager)

            # Assertions: websocket not used, manager not invoked (would have raised)
            self.assertIsNone(ws.sent)

        asyncio.get_event_loop().run_until_complete(run())
