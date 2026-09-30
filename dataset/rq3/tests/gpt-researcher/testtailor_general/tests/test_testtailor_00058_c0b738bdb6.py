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
        """Logger.info raises UnicodeEncodeError -> fallback logger.error called with replaced text"""
        # Arrange: replace the logger in the stream_output module globals with a fake one
        orig_logger = stream_output.__globals__['logger']

        class FakeLogger:
            def __init__(self):
                self.last_error = None

            def info(self, msg):
                # Simulate a UnicodeEncodeError being raised by the real logger
                # Note: the second argument to UnicodeEncodeError must be a str
                raise UnicodeEncodeError("codec", "x", 0, 1, "reason")

            def error(self, msg):
                # record the message passed to error
                self.last_error = msg

        fake = FakeLogger()
        stream_output.__globals__['logger'] = fake

        try:
            # Use an output string containing a character not encodable in cp1252 (e.g., emoji)
            output = "hello 😊"
            expected_fallback = output.encode("cp1252", errors="replace").decode("cp1252")

            # Act: call the async function (no websocket so (not websocket or output_log) is True)
            asyncio = __import__('asyncio')
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    stream_output(type="text", content="c", output=output)
                )
            finally:
                loop.close()

            # Assert: logger.error should have been called with the fallback/encoded string
            self.assertEqual(fake.last_error, expected_fallback)
        finally:
            # Restore original logger to avoid side effects for other tests
            stream_output.__globals__['logger'] = orig_logger
