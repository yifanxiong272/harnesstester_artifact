import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.groq.serializer')
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
        """Serialize a mixed list of text and image content parts for a user message."""
        text_part = ContentPartTextParam(text='Hello world')
        image_url = ImageURL(url='http://example.com/pic.png', detail='high')  # 'high' is an allowed literal
        image_part = ContentPartImageParam(image_url=image_url)

        content = [text_part, image_part]

        result = GroqMessageSerializer._serialize_user_content(content)

        # Should return a list with two serialized parts
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

        text_res, image_res = result

        # helper to access fields whether the serialized part is a dict or an object
        def get_field(obj, field):
            if isinstance(obj, dict):
                return obj[field]
            return getattr(obj, field)

        # Validate text part serialization
        self.assertEqual(get_field(text_res, 'type'), 'text')
        self.assertEqual(get_field(text_res, 'text'), 'Hello world')

        # Validate image part serialization
        self.assertEqual(get_field(image_res, 'type'), 'image_url')
        image_url_obj = get_field(image_res, 'image_url')
        # image_url_obj may be a dict or an object
        if isinstance(image_url_obj, dict):
            self.assertEqual(image_url_obj['url'], 'http://example.com/pic.png')
            self.assertEqual(image_url_obj['detail'], 'high')
        else:
            self.assertEqual(image_url_obj.url, 'http://example.com/pic.png')
            self.assertEqual(image_url_obj.detail, 'high')
