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
        """Ensure that when max_tokens is set on ChatDeepSeek it is forwarded to the provider call."""
        import asyncio
        from types import SimpleNamespace

        # Create model instance with max_tokens set so branch `common['max_tokens'] = self.max_tokens` is taken
        model = ChatDeepSeek(max_tokens=123)

        # prepare a fake async create method to capture kwargs passed to the provider
        captured = {}

        async def fake_create(*args, **kwargs):
            # capture kwargs so we can assert max_tokens was passed through
            captured.update(kwargs)

            class FakeMessage:
                def __init__(self):
                    self.content = "fake response"

            class FakeChoice:
                def __init__(self):
                    self.message = FakeMessage()

            class FakeResp:
                def __init__(self):
                    self.choices = [FakeChoice()]

            return FakeResp()

        # build fake client structure matching expected shape: client.chat.completions.create(...)
        fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)))

        # patch the instance _client to return our fake client
        model._client = lambda: fake_client  # type: ignore

        # Call ainvoke (no output_format and no tools to exercise regular conversation path)
        result = asyncio.run(model.ainvoke(messages=[]))

        # Assert the returned completion is from our fake response
        self.assertEqual(result.completion, "fake response")

        # Assert that max_tokens was forwarded into the provider call kwargs
        self.assertIn("max_tokens", captured)
        self.assertEqual(captured["max_tokens"], 123)
