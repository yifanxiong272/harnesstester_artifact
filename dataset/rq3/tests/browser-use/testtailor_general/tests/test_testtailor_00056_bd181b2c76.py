import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.aws.serializer')
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
        """Verify _is_base64_image correctly identifies data:image/ URLs."""
        # Valid base64 image data URL should return True
        img_data_url = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA'
        self.assertTrue(AWSBedrockMessageSerializer._is_base64_image(img_data_url))

        # Other data: URLs that are not images should return False
        text_data_url = 'data:text/plain;base64,SGVsbG8sIHdvcmxkIQ=='
        self.assertFalse(AWSBedrockMessageSerializer._is_base64_image(text_data_url))

        # Regular HTTP/HTTPS URLs should return False
        http_url = 'https://example.com/image.png'
        self.assertFalse(AWSBedrockMessageSerializer._is_base64_image(http_url))

        # Check case-sensitivity: variant with different casing should be False
        mixed_case = 'Data:Image/png;base64,AABBCC'
        self.assertFalse(AWSBedrockMessageSerializer._is_base64_image(mixed_case))
