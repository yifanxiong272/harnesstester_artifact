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
        """Serialize a ContentPartImageParam to a ChatCompletionContentPartImageParam and verify fields.

        The serializer may return either a dict or a model-like object, so handle both cases.
        """
        # Create an ImageURL with a valid detail literal and wrap it in a ContentPartImageParam
        image_url = ImageURL(url='http://example.com/img.png', detail='auto')
        part = ContentPartImageParam(image_url=image_url)

        # Call the serializer under test
        result = OpenAIMessageSerializer._serialize_content_part_image(part)

        # Support both dict and attribute-style results
        if isinstance(result, dict):
            # dict-style: verify top-level type and nested image_url fields
            self.assertIn('type', result)
            self.assertEqual(result['type'], 'image_url')
            self.assertIn('image_url', result)
            img = result['image_url']
            # image_url may itself be a dict or model-like
            if isinstance(img, dict):
                self.assertEqual(img.get('url'), 'http://example.com/img.png')
                self.assertEqual(img.get('detail'), 'auto')
            else:
                self.assertEqual(getattr(img, 'url'), 'http://example.com/img.png')
                self.assertEqual(getattr(img, 'detail'), 'auto')
        else:
            # attribute-style: verify properties
            self.assertEqual(result.type, 'image_url')
            self.assertIsNotNone(result.image_url)
            self.assertEqual(result.image_url.url, 'http://example.com/img.png')
            self.assertEqual(result.image_url.detail, 'auto')
