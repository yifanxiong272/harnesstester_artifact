import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.cerebras.serializer')
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
    def test_case_01(self):
        """Ensure _serialize_text_part returns the text of the ContentPartTextParam."""
        part = ContentPartTextParam(text="Sample text with unicode ✨")
        result = CerebrasMessageSerializer._serialize_text_part(part)
        self.assertEqual(result, part.text)
        self.assertIsInstance(result, str)
