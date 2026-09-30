import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.cerebras.chat')
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
        """When the response contains a usage object, _get_usage should map fields correctly."""
        # Arrange
        model = ChatCerebras()  # use defaults

        class DummyUsage:
            def __init__(self, prompt_tokens, completion_tokens, total_tokens):
                self.prompt_tokens = prompt_tokens
                self.completion_tokens = completion_tokens
                self.total_tokens = total_tokens

        class DummyResponse:
            def __init__(self, usage):
                self.usage = usage

        dummy_usage = DummyUsage(prompt_tokens=5, completion_tokens=7, total_tokens=12)
        resp = DummyResponse(usage=dummy_usage)

        # Act
        usage = model._get_usage(resp)

        # Assert
        self.assertIsNotNone(usage)
        self.assertIsInstance(usage, ChatInvokeUsage)
        self.assertEqual(usage.prompt_tokens, 5)
        self.assertIsNone(usage.prompt_cached_tokens)
        self.assertIsNone(usage.prompt_cache_creation_tokens)
        self.assertIsNone(usage.prompt_image_tokens)
        self.assertEqual(usage.completion_tokens, 7)
        self.assertEqual(usage.total_tokens, 12)
