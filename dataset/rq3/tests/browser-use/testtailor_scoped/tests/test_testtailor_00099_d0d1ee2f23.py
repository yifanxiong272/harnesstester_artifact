import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.deepseek.serializer')
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
        """Ensure image parts are serialized and the image_url.url is accessed."""
        # Create lightweight dummy objects to avoid relying on ImageURL or ContentPartImageParam constructors
        class Obj:
            pass

        # data URL case (triggers startswith('data:') check)
        data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA"
        part = Obj()
        part.image_url = Obj()
        part.image_url.url = data_url
        result = DeepSeekMessageSerializer._serialize_image_part(part)
        expected = {'type': 'image_url', 'image_url': {'url': data_url}}
        self.assertEqual(result, expected)

        # normal URL case
        normal_url = "http://example.com/image.jpg"
        part2 = Obj()
        part2.image_url = Obj()
        part2.image_url.url = normal_url
        result2 = DeepSeekMessageSerializer._serialize_image_part(part2)
        expected2 = {'type': 'image_url', 'image_url': {'url': normal_url}}
        self.assertEqual(result2, expected2)
