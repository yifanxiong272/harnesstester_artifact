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
        """Test that _handle_streaming_response collects content and finish_reason correctly."""
        import asyncio

        # Build simple objects that mimic the streaming chunks structure
        class DummyDelta:
            def __init__(self, content=None):
                self.content = content

        class DummyChoice:
            def __init__(self, content=None, finish_reason=None):
                self.delta = DummyDelta(content)
                self.finish_reason = finish_reason

        class DummyChunk:
            def __init__(self, choices):
                self.choices = choices

        async def async_response():
            # first chunk provides partial content without finish_reason
            yield DummyChunk([DummyChoice("Hello ", None)])
            # second chunk provides remaining content and a finish_reason
            yield DummyChunk([DummyChoice("World", "stop")])

        # Run the coroutine and assert the combined result
        loop = asyncio.get_event_loop()
        full_response, finish_reason = loop.run_until_complete(_handle_streaming_response(async_response()))
        self.assertEqual(full_response, "Hello World")
        self.assertEqual(finish_reason, "stop")
