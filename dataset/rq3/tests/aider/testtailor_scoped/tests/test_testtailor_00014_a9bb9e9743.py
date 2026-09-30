import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.gui')
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
        """Create a temporary directory and monkeypatch os.walk for 'aider', call search() and search(filter)."""
        tmpdir = __import__('tempfile').mkdtemp()
        sub_name = "subxyz_unique"
        subdir = os.path.join(tmpdir, sub_name)
        os.makedirs(subdir, exist_ok=True)
        f1 = os.path.join(tmpdir, "file1.txt")
        f2 = os.path.join(subdir, "file2.txt")
        for p in (f1, f2):
            with open(p, "w") as fh:
                fh.write("test")

        orig_walk = os.walk

        def fake_walk(root, topdown=True, onerror=None, followlinks=False):
            # Redirect walks for "aider" to our temporary directory
            if root == "aider":
                yield from orig_walk(tmpdir, topdown, onerror, followlinks)
            else:
                yield from orig_walk(root, topdown, onerror, followlinks)

        os.walk = fake_walk
        try:
            # Call without filter: should find both files
            results_all = search()
            self.assertIsInstance(results_all, list)
            expected_all = {os.path.normpath(f1), os.path.normpath(f2)}
            self.assertSetEqual(set(map(os.path.normpath, results_all)), expected_all)

            # Call with filter that matches the subdir: should find only f2
            results_sub = search(sub_name)
            self.assertIsInstance(results_sub, list)
            expected_sub = {os.path.normpath(f2)}
            self.assertSetEqual(set(map(os.path.normpath, results_sub)), expected_sub)
        finally:
            # Restore os.walk and clean up temp dir
            os.walk = orig_walk
            __import__('shutil').rmtree(tmpdir, ignore_errors=True)
