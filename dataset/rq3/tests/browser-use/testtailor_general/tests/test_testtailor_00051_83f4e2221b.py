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
        """Verify _is_base64_image correctly detects 'data:image/' prefix."""
        # Positive case: typical base64 JPEG data URL
        jpeg_data_url = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD...'
        self.assertTrue(AnthropicMessageSerializer._is_base64_image(jpeg_data_url))

        # Negative case: data URL but not an image media type
        json_data_url = 'data:application/json;base64,eyJrZXkiOiAidmFsdWUifQ=='
        self.assertFalse(AnthropicMessageSerializer._is_base64_image(json_data_url))

        # Negative case: regular HTTP URL
        http_url = 'https://example.com/image.png'
        self.assertFalse(AnthropicMessageSerializer._is_base64_image(http_url))

        # Case-sensitivity: function should be case-sensitive and return False
        mixed_case_data_url = 'Data:Image/png;base64,AAA'
        self.assertFalse(AnthropicMessageSerializer._is_base64_image(mixed_case_data_url))

        # Empty string should safely return False
        self.assertFalse(AnthropicMessageSerializer._is_base64_image(''))
