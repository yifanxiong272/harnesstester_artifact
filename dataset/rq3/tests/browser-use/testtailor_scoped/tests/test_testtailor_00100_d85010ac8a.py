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
        """Ensure _serialize_image_part reads part.image_url.url and returns expected dict for both normal and data URLs."""
        class DummyImageURL:
            def __init__(self, url: str):
                self.url = url

        class DummyPart:
            def __init__(self, url: str):
                self.image_url = DummyImageURL(url)

        # Normal URL case
        normal_url = 'https://example.com/image.png'
        part_normal = DummyPart(normal_url)
        result_normal = CerebrasMessageSerializer._serialize_image_part(part_normal)
        self.assertEqual(result_normal, {'type': 'image_url', 'image_url': {'url': normal_url}})

        # Data URL case (starts with 'data:')
        data_url = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA'
        part_data = DummyPart(data_url)
        result_data = CerebrasMessageSerializer._serialize_image_part(part_data)
        self.assertEqual(result_data, {'type': 'image_url', 'image_url': {'url': data_url}})
