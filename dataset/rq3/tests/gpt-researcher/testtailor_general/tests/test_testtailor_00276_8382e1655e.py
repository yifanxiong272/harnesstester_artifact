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
        """Test that an exception from websocket.send_json is caught and logged."""
        # Prepare a websocket whose send_json raises
        class BadWebSocket:
            async def send_json(self, *args, **kwargs):
                raise Exception("send failed")

        ws = BadWebSocket()

        # Replace the module logger with a mock so we can assert error was called
        original_logger = stream_output.__globals__.get("logger")
        mock_logger = unittest.mock.Mock()
        stream_output.__globals__['logger'] = mock_logger

        try:
            # Use __import__ to get asyncio without a top-level import statement
            asyncio = __import__('asyncio')
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Run the async function
                loop.run_until_complete(
                    stream_output("info", "step1", "some content", websocket=ws)
                )
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

            # Assert logger.error was called and the message contains the exception text
            self.assertTrue(mock_logger.error.called, "logger.error was not called")
            called_args = mock_logger.error.call_args[0]
            self.assertGreaterEqual(len(called_args), 1)
            msg = called_args[0]
            self.assertIn("Error streaming output:", msg)
            self.assertIn("send failed", msg)
        finally:
            # Restore original logger to avoid side effects on other tests
            stream_output.__globals__['logger'] = original_logger
