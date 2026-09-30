import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.openai.chat')
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
        """Ensure _get_usage returns a ChatInvokeUsage with fields mapped from response.usage.

        Covers both when prompt_tokens_details is present and when it is None.
        """
        # Create a ChatOpenAI instance (only model required for this test)
        model = ChatOpenAI(model='o3')

        # Minimal helper objects to simulate the ChatCompletion response shape used by _get_usage
        class PromptTokensDetails:
            def __init__(self, cached_tokens):
                self.cached_tokens = cached_tokens

        class Usage:
            def __init__(self, prompt_tokens, cached_tokens, completion_tokens, total_tokens, has_details=True):
                self.prompt_tokens = prompt_tokens
                self.prompt_tokens_details = PromptTokensDetails(cached_tokens) if has_details else None
                self.completion_tokens = completion_tokens
                self.total_tokens = total_tokens

        class Response:
            def __init__(self, usage):
                self.usage = usage

        # Case 1: prompt_tokens_details present
        usage_obj = Usage(prompt_tokens=123, cached_tokens=12, completion_tokens=45, total_tokens=168, has_details=True)
        response = Response(usage_obj)

        result = model._get_usage(response)
        self.assertIsNotNone(result)
        self.assertEqual(result.prompt_tokens, 123)
        self.assertEqual(result.prompt_cached_tokens, 12)
        self.assertEqual(result.completion_tokens, 45)
        self.assertEqual(result.total_tokens, 168)
        self.assertIsNone(result.prompt_cache_creation_tokens)
        self.assertIsNone(result.prompt_image_tokens)

        # Case 2: prompt_tokens_details is None -> prompt_cached_tokens should be None
        usage_obj2 = Usage(prompt_tokens=200, cached_tokens=0, completion_tokens=50, total_tokens=250, has_details=False)
        response2 = Response(usage_obj2)

        result2 = model._get_usage(response2)
        self.assertIsNotNone(result2)
        self.assertEqual(result2.prompt_tokens, 200)
        self.assertIsNone(result2.prompt_cached_tokens)
        self.assertEqual(result2.completion_tokens, 50)
        self.assertEqual(result2.total_tokens, 250)
