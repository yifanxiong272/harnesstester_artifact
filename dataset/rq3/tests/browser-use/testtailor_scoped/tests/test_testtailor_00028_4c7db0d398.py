import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.anthropic.serializer')
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
        """Verify _is_base64_image correctly identifies base64 image data URLs."""
        serializer = AnthropicMessageSerializer

        # Typical valid base64 image data URLs
        self.assertTrue(serializer._is_base64_image('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA'))
        self.assertTrue(serializer._is_base64_image('data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD'))

        # Non-image data URLs should be False
        self.assertFalse(serializer._is_base64_image('data:application/json;base64,eyJrZXkiOiAidmFsdWUifQ=='))

        # Regular URLs and other strings should be False
        self.assertFalse(serializer._is_base64_image('http://example.com/image.png'))
        self.assertFalse(serializer._is_base64_image(''))
        # Must include the slash after "data:image" to be considered an image
        self.assertFalse(serializer._is_base64_image('data:image')) 
        # Case-sensitive check: should be False
        self.assertFalse(serializer._is_base64_image('Data:Image/PNG;base64,AAA'))
