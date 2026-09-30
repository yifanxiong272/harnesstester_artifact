import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.repomap')
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
        """Test that find_src_files walks a directory and returns full file paths."""
        # Import needed modules locally to avoid top-level import requirement
        import tempfile
        import shutil
        import os

        temp_dir = tempfile.mkdtemp()
        try:
            # Create a file in the root temp directory
            file_root = os.path.join(temp_dir, "root_file.txt")
            with open(file_root, "w") as f:
                f.write("root")

            # Create a subdirectory with a file inside
            sub_dir = os.path.join(temp_dir, "subdir")
            os.mkdir(sub_dir)
            file_sub = os.path.join(sub_dir, "child_file.py")
            with open(file_sub, "w") as f:
                f.write("child")

            # Call the function under test (should take the os.walk path)
            result = find_src_files(temp_dir)

            # Verify result is a list and contains both files (order may vary)
            self.assertIsInstance(result, list)
            self.assertEqual(set(result), {file_root, file_sub})
            # Also ensure the loop was entered by checking we got more than zero files
            self.assertGreater(len(result), 0)
        finally:
            shutil.rmtree(temp_dir)
