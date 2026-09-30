import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.kaggle_crawler')
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
        """When a local description.md exists and force is False, the function should load and return its contents."""
        competition = "dummy_comp"
        # Use a path under the current working directory to avoid relying on tempfile/os imports
        base_dir = Path.cwd() / f"tmp_test_crawl_{id(self)}"
        comp_dir = base_dir / competition
        desc_fp = comp_dir / "description.md"
        try:
            comp_dir.mkdir(parents=True, exist_ok=True)
            expected_text = "This is a test description for the competition."
            desc_fp.write_text(expected_text, encoding="utf-8")

            # Call the function under test; it should short-circuit and return the file contents
            result = crawl_descriptions(competition=competition, local_data_path=str(base_dir), wait=0.0, force=False)

            self.assertIsInstance(result, str)
            self.assertEqual(result, expected_text)
        finally:
            # cleanup
            try:
                if desc_fp.exists():
                    desc_fp.unlink()
            except Exception:
                pass
            try:
                if comp_dir.exists():
                    comp_dir.rmdir()
            except Exception:
                pass
            try:
                if base_dir.exists():
                    base_dir.rmdir()
            except Exception:
                pass
