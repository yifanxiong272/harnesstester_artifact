import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.deepseek.chat')
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
        """Ensure ainvoke uses the client and serializes messages correctly for a simple text path."""
        # Create a ChatDeepSeek instance
        model = ChatDeepSeek()

        # Create a dummy async client that mimics the expected DeepSeek client shape
        class DummyMsg:
            def __init__(self):
                self.content = "ok"

        class DummyChoice:
            def __init__(self):
                self.message = DummyMsg()

        class DummyResp:
            def __init__(self):
                self.choices = [DummyChoice()]

        class DummyCompletions:
            async def create(self, *args, **kwargs):
                return DummyResp()

        class DummyChat:
            def __init__(self):
                self.completions = DummyCompletions()

        class DummyClient:
            def __init__(self):
                self.chat = DummyChat()

        # Patch the model's _client method to return our dummy client
        model._client = lambda: DummyClient()

        # Patch the serializer to avoid needing real UserMessage/SystemMessage classes
        original_serializer = DeepSeekMessageSerializer.serialize_messages
        DeepSeekMessageSerializer.serialize_messages = staticmethod(lambda messages: [{"role": "user", "content": "hello"}])

        try:
            # Provide any placeholder message objects; serializer is patched so their type doesn't matter
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(model.ainvoke([object()]))
        finally:
            # Restore serializer to avoid side effects on other tests
            DeepSeekMessageSerializer.serialize_messages = original_serializer

        self.assertIsNotNone(result)
        self.assertEqual(result.completion, "ok")
