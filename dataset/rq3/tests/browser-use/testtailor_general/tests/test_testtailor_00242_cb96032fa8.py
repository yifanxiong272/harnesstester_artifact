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
    def test_case_XX(self):
        """Ensure _serialize_image_part reads the image_url.url and returns the expected dict."""
        # create a ContentPartImageParam using a dict for image_url so pydantic will parse it
        part = ContentPartImageParam(image_url={'url': 'http://example.com/image.png'})
        result = CerebrasMessageSerializer._serialize_image_part(part)
        expected = {'type': 'image_url', 'image_url': {'url': 'http://example.com/image.png'}}
        self.assertEqual(result, expected)
