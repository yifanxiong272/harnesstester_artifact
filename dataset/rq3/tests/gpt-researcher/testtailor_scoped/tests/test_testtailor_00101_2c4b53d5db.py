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
        """Ensure MCPStreamer.stream_log calls logger.info with the provided message."""
        message = "stream log test message"
        streamer = MCPStreamer(websocket=None)

        with unittest.mock.patch.object(logging.Logger, "info") as mock_info:
            # Run the async coroutine to exercise the target logger.info in stream_log
            asyncio.run(streamer.stream_log(message))

            # Ensure the patched info method was called
            self.assertTrue(mock_info.called, "logger.info was not called")

            # Be robust to whether the logger instance is passed as the first arg or not.
            called_args, called_kwargs = mock_info.call_args
            if len(called_args) >= 2:
                observed_message = called_args[1]
            else:
                observed_message = called_args[0]
            self.assertEqual(observed_message, message)
