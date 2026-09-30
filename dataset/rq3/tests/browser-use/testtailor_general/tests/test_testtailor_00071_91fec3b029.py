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
        """Test that a ContentPartTextParam is serialized to a ChatCompletionContentPartTextParam with correct fields."""
        part = ContentPartTextParam(text="sample text")
        result = GroqMessageSerializer._serialize_content_part_text(part)

        # Support both mapping-like and attribute-like return types
        if isinstance(result, dict) or hasattr(result, "__getitem__"):
            self.assertEqual(result["text"], "sample text")
            self.assertEqual(result["type"], "text")
        else:
            self.assertEqual(getattr(result, "text"), "sample text")
            self.assertEqual(getattr(result, "type"), "text")
