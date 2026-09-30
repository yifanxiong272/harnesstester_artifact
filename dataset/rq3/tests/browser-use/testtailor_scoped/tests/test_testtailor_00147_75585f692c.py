import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.ollama.serializer')
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
        """Ensure _extract_text_content collects text and refusal parts and ignores others."""
        # Helper simple part class
        class Part:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        # Build content with various part types:
        content = [
            Part(type='text', text='Hello'),
            Part(type='image_url', image_url=Part(url='http://example.com/img.png')),  # should be skipped
            Part(type='refusal', refusal='No access'),
            Part(type='text', text='World'),
            Part()  # no 'type' attribute -> ignored
        ]

        result = OllamaMessageSerializer._extract_text_content(content)
        self.assertEqual(result, 'Hello\n[Refusal] No access\nWorld')
