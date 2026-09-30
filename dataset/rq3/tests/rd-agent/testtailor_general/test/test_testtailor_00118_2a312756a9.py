import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.log.storage')
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
        """Ensure _remove_empty_dir removes only empty directories (including nested) and leaves non-empty ones."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()

            # Create an empty directory with a nested empty subdirectory
            dir_empty = root / "dir_empty"
            dir_empty.mkdir()
            sub_empty = dir_empty / "sub_empty"
            sub_empty.mkdir()

            # Create a directory that contains a file (should not be removed)
            dir_with_file = root / "dir_with_file"
            dir_with_file.mkdir()
            file_in_dir = dir_with_file / "keep.txt"
            file_in_dir.write_text("keep")

            # Create a file at root (should prevent root from being removed)
            root_file = root / "root.txt"
            root_file.write_text("root")

            # Sanity checks before running the function
            self.assertTrue(root.is_dir())
            self.assertTrue(dir_empty.is_dir())
            self.assertTrue(sub_empty.is_dir())
            self.assertTrue(dir_with_file.is_dir())
            self.assertTrue(file_in_dir.is_file())
            self.assertTrue(root_file.is_file())

            # Call the function under test
            _remove_empty_dir(root)

            # The empty nested directories should be removed
            self.assertFalse(sub_empty.exists(), "Nested empty directory should be removed")
            self.assertFalse(dir_empty.exists(), "Empty directory should be removed after its empty subdirs are removed")

            # Non-empty directory and files should remain
            self.assertTrue(dir_with_file.exists(), "Directory that contains a file should remain")
            self.assertTrue(file_in_dir.exists(), "File inside non-empty directory should remain")
            self.assertTrue(root_file.exists(), "File at root should remain")

            # Root should remain because it contains non-empty entries
            self.assertTrue(root.exists(), "Root directory should remain since it is not empty")
