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
        """Ensure _ensure_output_dir uses output_dir/images when research_id is empty."""
        tempfile = __import__('tempfile')
        shutil = __import__('shutil')
        pathlib = __import__('pathlib')
        Path = pathlib.Path

        tmpdir = tempfile.mkdtemp()
        try:
            # Instantiate provider with custom output_dir
            provider = ImageGeneratorProvider(output_dir=tmpdir)

            # Call without research_id (default empty) -> should use output_dir/images
            result_path = provider._ensure_output_dir()

            expected_path = Path(tmpdir) / "images"

            # Assertions: returned path matches expected and directory was created
            self.assertIsInstance(result_path, Path)
            self.assertEqual(result_path.resolve(), expected_path.resolve())
            self.assertTrue(expected_path.exists())
            self.assertTrue(expected_path.is_dir())
        finally:
            # Cleanup temporary directory
            shutil.rmtree(tmpdir, ignore_errors=True)
