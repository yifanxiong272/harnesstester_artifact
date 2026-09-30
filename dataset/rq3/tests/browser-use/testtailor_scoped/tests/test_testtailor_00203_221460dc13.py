import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.groq.chat')
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
        """Verify _get_usage returns a ChatInvokeUsage populated from response.usage and None when usage is None."""
        groq = ChatGroq(model='test-model')

        class UsageObj:
            def __init__(self, prompt_tokens, completion_tokens, total_tokens):
                self.prompt_tokens = prompt_tokens
                self.completion_tokens = completion_tokens
                self.total_tokens = total_tokens

        class ResponseObj:
            def __init__(self, usage):
                self.usage = usage

        # Create a fake response with usage populated
        usage_obj = UsageObj(prompt_tokens=5, completion_tokens=7, total_tokens=12)
        response = ResponseObj(usage=usage_obj)

        usage = groq._get_usage(response)

        # Assert we received a ChatInvokeUsage with fields mapped correctly
        self.assertIsNotNone(usage)
        self.assertIsInstance(usage, ChatInvokeUsage)
        self.assertEqual(usage.prompt_tokens, 5)
        self.assertEqual(usage.completion_tokens, 7)
        self.assertEqual(usage.total_tokens, 12)
        # Groq doesn't support cache/image tokens, ensure they are None
        self.assertIsNone(usage.prompt_cached_tokens)
        self.assertIsNone(usage.prompt_cache_creation_tokens)
        self.assertIsNone(usage.prompt_image_tokens)

        # When response.usage is None, the method should return None
        response_none = ResponseObj(usage=None)
        self.assertIsNone(groq._get_usage(response_none))
