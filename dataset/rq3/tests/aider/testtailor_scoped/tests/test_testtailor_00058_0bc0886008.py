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
        """Test find_src_files for a real directory and for a non-directory path."""
        # Use __import__ so we don't need to add import statements at top-level
        tempfile = __import__("tempfile")
        shutil = __import__("shutil")
        os = __import__("os")

        # Create a temporary directory structure with some files to trigger the
        # directory branch (which initializes src_files = []) and uses os.walk.
        tmpdir = tempfile.mkdtemp()
        try:
            # Create files and a nested directory
            file1 = os.path.join(tmpdir, "file1.txt")
            subdir = os.path.join(tmpdir, "sub")
            os.mkdir(subdir)
            file2 = os.path.join(subdir, "file2.py")

            # Write simple content to ensure files exist
            with open(file1, "w") as f:
                f.write("hello")
            with open(file2, "w") as f:
                f.write("print('hi')")

            # Call the function under test - should traverse and collect both files
            result = find_src_files(tmpdir)

            # Expect both files (order is not guaranteed)
            expected = {os.path.normpath(file1), os.path.normpath(file2)}
            got = {os.path.normpath(p) for p in result}

            self.assertEqual(expected, got, "find_src_files should return all files under the directory")
        finally:
            # Clean up the temporary directory
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

        # Also test the non-directory branch: when path is not a directory, function
        # should return a single-element list containing the provided path.
        # Create a temporary file and use its path (it's not a directory)
        tmpf = tempfile.NamedTemporaryFile(delete=False)
        tmpf_path = tmpf.name
        tmpf.close()
        try:
            # Ensure the path exists and is a file (not a directory)
            self.assertTrue(os.path.exists(tmpf_path))
            self.assertFalse(os.path.isdir(tmpf_path))

            single_result = find_src_files(tmpf_path)
            self.assertEqual(single_result, [tmpf_path])
        finally:
            try:
                os.remove(tmpf_path)
            except Exception:
                pass
