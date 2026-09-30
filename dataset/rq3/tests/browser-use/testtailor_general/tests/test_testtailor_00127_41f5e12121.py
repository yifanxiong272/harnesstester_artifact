import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.openai.responses_serializer')
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
    def test_case_serialize_assistant_content_list_with_refusal(self):
        """Test that assistant content list initializes serialized_parts and handles text and refusal parts."""
        content = [
            ContentPartTextParam(type='text', text='Assistant reply.'),
            ContentPartRefusalParam(type='refusal', refusal='I cannot comply.'),
        ]
        result = ResponsesAPIMessageSerializer._serialize_assistant_content(content)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

        first, second = result
        # The serializer returns dict-like objects for the Responses API params in this test environment
        self.assertEqual(first['text'], 'Assistant reply.')
        self.assertEqual(first['type'], 'input_text')

        # Refusal parts are converted to text in the format "[Refusal: ...]"
        self.assertEqual(second['text'], '[Refusal: I cannot comply.]')
        self.assertEqual(second['type'], 'input_text')
