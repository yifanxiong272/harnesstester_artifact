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
    def test_serialize_assistant_content_with_text_and_refusal(self):
        """Test that assistant content list with text and refusal is serialized to input_text parts."""
        message = AssistantMessage(
            content=[
                ContentPartTextParam(type='text', text='Assistant answer part'),
                ContentPartRefusalParam(type='refusal', refusal='I cannot do that.'),
            ]
        )
        result = ResponsesAPIMessageSerializer.serialize(message)

        self.assertEqual(result['role'], 'assistant')
        self.assertIsInstance(result['content'], list)
        self.assertEqual(len(result['content']), 2)

        first = result['content'][0]
        second = result['content'][1]

        self.assertEqual(first.get('type'), 'input_text')
        self.assertEqual(first.get('text'), 'Assistant answer part')

        # Refusal should be converted to a text input with the refusal string embedded
        self.assertEqual(second.get('type'), 'input_text')
        self.assertEqual(second.get('text'), '[Refusal: I cannot do that.]')
