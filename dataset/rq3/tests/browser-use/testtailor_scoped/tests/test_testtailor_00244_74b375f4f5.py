import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.openai.serializer')
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
        """Serialize a list of content parts (text + image) for a user message."""
        # Create a text content part and an image content part
        text_part = ContentPartTextParam(text="Hello world")
        # ImageURL.detail must be one of the allowed literals ('auto', 'low', 'high')
        image_url = ImageURL(url="https://example.com/image.png", detail="auto")
        image_part = ContentPartImageParam(image_url=image_url)

        content = [text_part, image_part]

        # Call the serializer for user content (should take the list branch and create serialized_parts)
        result = OpenAIMessageSerializer._serialize_user_content(content)

        # Verify result is a list with two serialized parts
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

        # Helper to handle either pydantic models (attributes) or dicts (mapping)
        def _get(obj, key):
            if hasattr(obj, key):
                return getattr(obj, key)
            return obj[key]

        # First part should be serialized text
        first = result[0]
        first_text = _get(first, 'text')
        first_type = _get(first, 'type')
        self.assertEqual(first_text, "Hello world")
        self.assertEqual(first_type, 'text')

        # Second part should be serialized image
        second = result[1]
        image_obj = _get(second, 'image_url')
        # image_obj may itself be a model or dict
        image_url_val = _get(image_obj, 'url')
        image_detail_val = _get(image_obj, 'detail')
        second_type = _get(second, 'type')

        self.assertEqual(image_url_val, "https://example.com/image.png")
        self.assertEqual(image_detail_val, "auto")
        self.assertEqual(second_type, 'image_url')
