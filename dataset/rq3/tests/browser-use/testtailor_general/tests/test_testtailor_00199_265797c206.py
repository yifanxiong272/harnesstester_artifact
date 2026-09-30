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
        """Check _is_url_image correctly identifies HTTP/HTTPS image URLs with supported extensions and rejects others."""
        fn = AWSBedrockMessageSerializer._is_url_image

        # Positive cases: http/https with supported extensions (case-insensitive)
        self.assertTrue(fn('http://example.com/image.JPG'))
        self.assertTrue(fn('https://example.com/path/photo.png'))
        self.assertTrue(fn('https://example.com/assets/picture.webp'))
        self.assertTrue(fn('http://example.com/graphic.bmp'))
        self.assertTrue(fn('https://example.com/album/photo.jpeg'))

        # Negative cases: unsupported scheme, unsupported extension, query strings break simple endswith check
        self.assertFalse(fn('ftp://example.com/image.jpg'))               # wrong scheme
        self.assertFalse(fn('http://example.com/document.txt'))           # unsupported extension
        self.assertFalse(fn('https://example.com/image.jpg?size=1'))      # query string means it doesn't end with extension
        self.assertFalse(fn('http://example.com/imagejpg'))               # missing dot before extension
