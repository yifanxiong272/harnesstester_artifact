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
        """complete the test case here"""
        # Create simple stand-ins for the Pydantic models to avoid needing imports
        class DummyImageURL:
            def __init__(self, url: str):
                self.url = url

            def __repr__(self) -> str:
                return f"DummyImageURL(url={self.url!r})"

        class DummyPart:
            def __init__(self, image_url: DummyImageURL):
                self.image_url = image_url

            def __repr__(self) -> str:
                return f"DummyPart(image_url={self.image_url!r})"

        # Case 1: data URL (should follow the branch that checks startswith('data:'))
        data_url = 'data:image/png;base64,AAAA'
        part_data = DummyPart(DummyImageURL(data_url))
        result_data = DeepSeekMessageSerializer._serialize_image_part(part_data)
        self.assertIsInstance(result_data, dict)
        self.assertEqual(result_data, {'type': 'image_url', 'image_url': {'url': data_url}})

        # Case 2: normal URL (other branch)
        normal_url = 'https://example.com/image.png'
        part_normal = DummyPart(DummyImageURL(normal_url))
        result_normal = DeepSeekMessageSerializer._serialize_image_part(part_normal)
        self.assertIsInstance(result_normal, dict)
        self.assertEqual(result_normal, {'type': 'image_url', 'image_url': {'url': normal_url}})
