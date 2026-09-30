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
        """Ensure _ensure_output_dir creates outputs/images/{research_id} when research_id provided."""
        # Use a unique directory name without relying on external imports
        unique_dir = f"test_outputs_{id(self)}_{id(object())}"
        provider = ImageGeneratorProvider(output_dir=unique_dir)
        research_id = "research123"
        try:
            result = provider._ensure_output_dir(research_id)
            expected = provider.output_dir / "images" / research_id

            # Returned path should match expected and directory should exist
            self.assertEqual(result, expected)
            self.assertTrue(expected.exists())
            self.assertTrue(expected.is_dir())
        finally:
            # Cleanup created directory tree using pathlib methods only
            root = provider.output_dir
            try:
                if root.exists():
                    # Remove all children (files and directories) bottom-up
                    for p in sorted(root.rglob('*'), key=lambda p: p.as_posix(), reverse=True):
                        try:
                            if p.is_file() or p.is_symlink():
                                p.unlink()
                            elif p.is_dir():
                                p.rmdir()
                        except Exception:
                            # best-effort cleanup; ignore errors during removal
                            pass
                    # Remove the root directory itself
                    try:
                        root.rmdir()
                    except Exception:
                        pass
            except Exception:
                pass
