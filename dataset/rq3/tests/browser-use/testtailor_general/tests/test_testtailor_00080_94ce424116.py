import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.openai.serializer')
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
        """Serialize ContentPartTextParam to ChatCompletionContentPartTextParam"""
        part = ContentPartTextParam(text="hello world")
        result = OpenAIMessageSerializer._serialize_content_part_text(part)

        # ChatCompletionContentPartTextParam is a TypedDict, so avoid isinstance checks against it.
        self.assertIsInstance(result, dict)
        self.assertIn('text', result)
        self.assertIn('type', result)
        self.assertEqual(result['text'], "hello world")
        self.assertEqual(result['type'], "text")
