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
        """Verify that a ContentPartTextParam is serialized to the expected structure."""
        part = ContentPartTextParam(text="hello world")
        result = OpenAIMessageSerializer._serialize_content_part_text(part)

        # The serializer returns a TypedDict-like mapping. Avoid isinstance checks against the TypedDict type.
        # Support either dict-like or attribute access objects (be permissive for different implementations).
        if isinstance(result, dict):
            self.assertEqual(result.get('text'), "hello world")
            self.assertEqual(result.get('type'), "text")
            # Also assert exact structure
            self.assertEqual(result, {"text": "hello world", "type": "text"})
        else:
            # Fallback: object with attributes
            self.assertEqual(getattr(result, 'text'), "hello world")
            self.assertEqual(getattr(result, 'type'), "text")
