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
        """Verify parsing of base64 data URLs for supported and unsupported media types."""
        # Supported media type should be returned as-is and data extracted after the comma
        url_png = 'data:image/png;base64,AAA'
        media_type, data = AnthropicMessageSerializer._parse_base64_url(url_png)
        self.assertEqual(media_type, 'image/png')
        self.assertEqual(data, 'AAA')

        # Unsupported media type should default to image/jpeg while still returning the data
        url_unsupported = 'data:image/xyz;base64,BBBCCC'
        media_type2, data2 = AnthropicMessageSerializer._parse_base64_url(url_unsupported)
        self.assertEqual(media_type2, 'image/jpeg')
        self.assertEqual(data2, 'BBBCCC')
