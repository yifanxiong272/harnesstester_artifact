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
        """Serialize a ContentPartImageParam into a ChatCompletionContentPartImageParam."""
        # use a valid detail literal per the ImageURL type ('auto', 'low', or 'high')
        img = ImageURL(url='http://example.com/img.png', detail='auto')
        part = ContentPartImageParam(image_url=img)

        result = GroqMessageSerializer._serialize_content_part_image(part)

        # Support both dict-like and attribute access return types
        if isinstance(result, dict):
            self.assertIn('image_url', result)
            self.assertIn('type', result)
            self.assertEqual(result['image_url']['url'], part.image_url.url)
            self.assertEqual(result['image_url']['detail'], part.image_url.detail)
            self.assertEqual(result['type'], 'image_url')
        else:
            self.assertTrue(hasattr(result, 'image_url'))
            self.assertTrue(hasattr(result, 'type'))
            self.assertEqual(result.image_url.url, part.image_url.url)
            self.assertEqual(result.image_url.detail, part.image_url.detail)
            self.assertEqual(result.type, 'image_url')
