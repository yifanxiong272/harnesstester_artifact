import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.litellm.serializer')
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
		"""Test serialization of a mixed list of text and image parts for user content."""
		text_part = ContentPartTextParam(text="Hello world")
		# Provide image_url as a dict with a valid 'detail' literal value so pydantic can coerce it
		image_part = ContentPartImageParam(image_url={"url": "http://example.com/pic.png", "detail": "auto"})

		result = LiteLLMMessageSerializer._serialize_user_content([text_part, image_part])

		expected = [
			{'type': 'text', 'text': 'Hello world'},
			{
				'type': 'image_url',
				'image_url': {
					'url': 'http://example.com/pic.png',
					'detail': 'auto',
				},
			},
		]

		self.assertEqual(result, expected)
