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
        """Ensure stream_log_sync schedules an async task when an event loop is running."""
        streamer = MCPStreamer(websocket=object())

        # Create a fake running loop
        mock_loop = Mock()
        mock_loop.is_running.return_value = True

        # Patch asyncio.get_event_loop to return our running loop and patch create_task to observe calls.
        with patch.object(asyncio, "get_event_loop", return_value=mock_loop):
            with patch.object(asyncio, "create_task") as mock_create:
                # Replace stream_log with an AsyncMock so calling it returns a coroutine without side effects.
                async_mock = AsyncMock()
                with patch.object(streamer, "stream_log", new=async_mock):
                    # Call the synchronous helper; should route to asyncio.create_task(...)
                    streamer.stream_log_sync("test message", {"x": 1})

                # create_task should have been called exactly once with a coroutine
                mock_create.assert_called_once()
                created_arg = mock_create.call_args[0][0]
                # The argument passed to create_task should be a coroutine object
                self.assertTrue(asyncio.iscoroutine(created_arg))
