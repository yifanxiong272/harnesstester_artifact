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
        """When a local description.md exists and force is False, the function should load and return its text."""
        competition = "test_comp"
        # create a temporary directory using tempfile via __import__ to avoid relying on top-level imports
        tmpdir = __import__("tempfile").mkdtemp()
        try:
            local_data_path = tmpdir
            comp_dir = Path(local_data_path) / competition
            comp_dir.mkdir(parents=True, exist_ok=True)

            desc_file = comp_dir / "description.md"
            expected_content = "# Example\nThis is a test description."
            # write the file
            desc_file.write_text(expected_content, encoding="utf-8")

            # Call the function; it should return the file contents (string) without trying to use webdriver
            result = crawl_descriptions(competition, local_data_path, wait=0.01, force=False)

            self.assertIsInstance(result, str)
            self.assertEqual(result, expected_content)
        finally:
            # cleanup the temporary directory
            __import__("shutil").rmtree(tmpdir, ignore_errors=True)
