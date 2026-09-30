import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.groq.serializer')
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
        """Ensure _serialize_content_part_text returns a mapping with same text and type 'text'."""
        # Create a ContentPartTextParam instance
        part = ContentPartTextParam(text="Hello, test!")

        # Call the target method
        result = GroqMessageSerializer._serialize_content_part_text(part)

        # The return type is a TypedDict (mapping), so check mapping behavior rather than isinstance against TypedDict
        self.assertIsInstance(result, dict)
        self.assertIn('text', result)
        self.assertIn('type', result)
        self.assertEqual(result['text'], part.text)
        self.assertEqual(result['type'], 'text')
