import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.remove_unfinished')
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
        """Ensure directories with a .traj file are detected and (dry_run vs actual) removal works."""
        # Use dynamic imports to avoid relying on top-level imports in the test harness
        tempfile = __import__("tempfile")
        pathlib = __import__("pathlib")
        json = __import__("json")

        Path = pathlib.Path

        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            # create a directory that matches the "__" name check
            subdir = base_dir / "run__001"
            subdir.mkdir()
            # create a valid .traj file (JSON) so load_file will succeed but has no submission
            traj_file = subdir / "result.traj"
            traj_file.write_text(json.dumps({"info": {}}))
            # Sanity: directory exists before calling
            self.assertTrue(subdir.exists())

            # Dry run should not remove the directory
            remove_unfinished(base_dir, dry_run=True)
            self.assertTrue(subdir.exists(), "Directory should remain during dry run")

            # Actual removal should remove the directory
            remove_unfinished(base_dir, dry_run=False)
            self.assertFalse(subdir.exists(), "Directory should be removed when dry_run=False")
