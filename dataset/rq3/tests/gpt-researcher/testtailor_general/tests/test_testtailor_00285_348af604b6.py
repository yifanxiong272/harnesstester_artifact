import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.llm_provider.image.image_generator')
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
        """Ensure _ensure_output_dir creates outputs/images/{research_id}/ when research_id provided."""
        # Use __import__ to avoid top-level import statements in this snippet
        tempfile = __import__('tempfile')
        pathlib = __import__('pathlib')
        Path = pathlib.Path

        with tempfile.TemporaryDirectory() as td:
            provider = ImageGeneratorProvider(output_dir=td)
            research_id = "res123"
            output_path = provider._ensure_output_dir(research_id)

            expected = Path(td) / "images" / research_id
            # Returned path should match expected and the directory should exist
            self.assertIsInstance(output_path, Path)
            self.assertEqual(output_path, expected)
            self.assertTrue(expected.exists())
            self.assertTrue(expected.is_dir())

            # Calling again should not raise and should return the same path
            output_path2 = provider._ensure_output_dir(research_id)
            self.assertEqual(output_path2, expected)
