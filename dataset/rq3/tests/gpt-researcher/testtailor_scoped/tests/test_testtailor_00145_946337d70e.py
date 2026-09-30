import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.llm_provider.image.modelslab_image_generator')
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
        """Ensure _ensure_output_dir creates the correct directories for both
        a provided research_id and when no research_id is given."""
        # Create a unique temporary-like directory name without importing tempfile.
        base = Path(f"tmp_modelslab_test_{id(self)}")

        # Ensure provider uses our base path
        provider = ModelsLabImageGeneratorProvider(output_dir=str(base))

        # Case 1: non-empty research_id -> <base>/images/<research_id>
        research_id = "test-research"
        path = provider._ensure_output_dir(research_id)
        expected_path = base / "images" / research_id
        self.assertTrue(path.exists(), "Expected directory to be created")
        self.assertTrue(path.is_dir(), "Expected a directory")
        self.assertEqual(Path(path), expected_path)

        # Calling again should be idempotent and not raise
        path2 = provider._ensure_output_dir(research_id)
        self.assertEqual(Path(path2), expected_path)

        # Case 2: empty research_id -> <base>/images
        path_no_id = provider._ensure_output_dir("")
        expected_no_id = base / "images"
        self.assertTrue(path_no_id.exists(), "Expected images directory to exist")
        self.assertTrue(path_no_id.is_dir())
        self.assertEqual(Path(path_no_id), expected_no_id)
