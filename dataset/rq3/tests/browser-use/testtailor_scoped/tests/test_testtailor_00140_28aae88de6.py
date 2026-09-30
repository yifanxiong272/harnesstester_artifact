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
        """Serialize a ContentPartRefusalParam into a ChatCompletionContentPartRefusalParam-like dict."""
        # Arrange: create a refusal content part
        refusal_text = "I refuse to provide that information."
        part = ContentPartRefusalParam(refusal=refusal_text)

        # Act: serialize using the OpenAIMessageSerializer helper
        result = OpenAIMessageSerializer._serialize_content_part_refusal(part)

        # Assert: result is a mapping with the expected fields and values
        self.assertIsInstance(result, dict)
        self.assertIn('refusal', result)
        self.assertIn('type', result)
        self.assertEqual(result['refusal'], refusal_text)
        self.assertEqual(result['type'], 'refusal')
