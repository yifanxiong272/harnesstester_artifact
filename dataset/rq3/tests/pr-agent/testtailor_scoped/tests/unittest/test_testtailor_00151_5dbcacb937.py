import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.algo.ai_handlers.litellm_helpers')
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
        """Streaming response has no content but provides a finish_reason -> raises APIError and logs debug."""
        async def fake_response():
            # create a chunk with a choice that has a delta without content and a finish_reason
            class Delta:
                pass  # no 'content' attribute

            class Choice:
                def __init__(self, delta):
                    self.delta = delta
                    self.finish_reason = "stop"

            chunk = type("Chunk", (), {"choices": [Choice(Delta())]})()
            yield chunk

        # prepare the async generator
        response = fake_response()

        # replace get_logger and openai.APIError in the function's globals with mocks/dummies
        globals_dict = _handle_streaming_response.__globals__
        original_get_logger = globals_dict.get("get_logger", None)
        original_openai_api_error = None
        if "openai" in globals_dict:
            original_openai_api_error = globals_dict["openai"].APIError

        mock_logger = unittest.mock.Mock()
        globals_dict["get_logger"] = lambda *a, **k: mock_logger

        # Provide a simpler APIError that accepts a single message so raising works in the test
        class DummyAPIError(Exception):
            def __init__(self, message, *args, **kwargs):
                super().__init__(message)

        globals_dict["openai"].APIError = DummyAPIError

        try:
            with self.assertRaises(DummyAPIError) as cm:
                # use __import__ to avoid adding an import statement for asyncio
                __import__('asyncio').run(_handle_streaming_response(response))

            # verify the raised error message mentions the finish_reason and no content
            self.assertIn("completed with finish_reason 'stop' but no content received", str(cm.exception))

            # verify debug was called with the expected message
            mock_logger.debug.assert_called_with(
                "Streaming response resulted in empty content but completed with finish_reason: stop"
            )
        finally:
            # restore original get_logger
            if original_get_logger is None:
                del globals_dict["get_logger"]
            else:
                globals_dict["get_logger"] = original_get_logger

            # restore original openai.APIError
            if original_openai_api_error is None:
                # If there was no original, remove attribute (unlikely), otherwise set back
                try:
                    del globals_dict["openai"].APIError
                except Exception:
                    pass
            else:
                globals_dict["openai"].APIError = original_openai_api_error
