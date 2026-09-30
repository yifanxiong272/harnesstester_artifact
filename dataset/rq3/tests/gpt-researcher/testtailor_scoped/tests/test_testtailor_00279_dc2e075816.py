import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.mcp.streaming')
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
        """Ensure stream_log_sync obtains the event loop and runs the async stream_log when websocket is present."""
        # Create streamer with a truthy websocket so the websocket branch is taken
        streamer = MCPStreamer(websocket=object())

        # Replace the async stream_log with an AsyncMock so no external imports/run happen
        async_mock = AsyncMock()
        streamer.stream_log = async_mock

        # Create a fresh event loop that is not running and patch asyncio.get_event_loop to return it
        loop = asyncio.new_event_loop()
        with patch("asyncio.get_event_loop", return_value=loop):
            try:
                streamer.stream_log_sync("test message", {"a": 1})
                # The patched async stream_log should have been scheduled/run via run_until_complete
                async_mock.assert_called_once_with("test message", {"a": 1})
            finally:
                loop.close()
