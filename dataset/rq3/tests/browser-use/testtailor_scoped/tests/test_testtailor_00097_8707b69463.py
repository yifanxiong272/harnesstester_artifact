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
        """Verify URL image detection for various schemes and extensions."""
        # Valid HTTP/HTTPS image URLs with different cases and extensions
        self.assertTrue(AWSBedrockMessageSerializer._is_url_image("http://example.com/path/image.jpg"))
        self.assertTrue(AWSBedrockMessageSerializer._is_url_image("https://example.com/IMG.PNG"))
        self.assertTrue(AWSBedrockMessageSerializer._is_url_image("https://example.com/photo.JPeg"))
        self.assertTrue(AWSBedrockMessageSerializer._is_url_image("http://example.com/anim.GIF"))
        self.assertTrue(AWSBedrockMessageSerializer._is_url_image("http://example.com/pic.webp"))
        self.assertTrue(AWSBedrockMessageSerializer._is_url_image("http://example.com/scan.BMP"))

        # Invalid cases: unsupported scheme, missing scheme, wrong extension, query params change the suffix
        self.assertFalse(AWSBedrockMessageSerializer._is_url_image("ftp://example.com/image.jpg"))
        self.assertFalse(AWSBedrockMessageSerializer._is_url_image("example.com/image.jpg"))
        self.assertFalse(AWSBedrockMessageSerializer._is_url_image("http://example.com/image.jpg?size=small"))
        self.assertFalse(AWSBedrockMessageSerializer._is_url_image("http://example.com/document.txt"))
