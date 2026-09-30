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
        """Ensure _ensure_output_dir creates and returns correct paths with and without research_id."""
        # Use a predictable but likely-unique test directory under CWD to avoid needing tempfile/shutil.
        td = Path(f"tmp_modelslab_test_dir_{os.getpid()}")
        provider = ModelsLabImageGeneratorProvider(api_key="fake-key", output_dir=str(td))

        base_images = td / "images"
        research_id = "research123"

        # Helper to recursively remove a directory without using shutil
        def _rmtree(path: Path):
            if not path.exists():
                return
            for root, dirs, files in os.walk(str(path), topdown=False):
                for name in files:
                    fp = Path(root) / name
                    try:
                        os.remove(str(fp))
                    except Exception:
                        try:
                            os.rmdir(str(fp))
                        except Exception:
                            pass
                for name in dirs:
                    dp = Path(root) / name
                    try:
                        os.rmdir(str(dp))
                    except Exception:
                        pass
            try:
                os.rmdir(str(path))
            except Exception:
                pass

        # Ensure clean start
        if td.exists():
            _rmtree(td)
        self.assertFalse(base_images.exists())

        try:
            # Call with a non-empty research_id -> should create outputs/images/<research_id>
            path_with_id = provider._ensure_output_dir(research_id)
            expected_with_id = base_images / research_id
            # returned value should match expected Path
            self.assertEqual(Path(path_with_id), expected_with_id)
            self.assertTrue(expected_with_id.exists() and expected_with_id.is_dir())

            # Call with empty research_id -> should return/create outputs/images
            path_no_id = provider._ensure_output_dir("")
            self.assertEqual(Path(path_no_id), base_images)
            self.assertTrue(base_images.exists() and base_images.is_dir())

            # Idempotency: calling again with the same research_id should succeed and return same path
            path_with_id_again = provider._ensure_output_dir(research_id)
            self.assertEqual(Path(path_with_id_again), expected_with_id)
            self.assertTrue(expected_with_id.exists())
        finally:
            # Cleanup created directories
            if td.exists():
                _rmtree(td)
