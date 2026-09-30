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
        """Directory without '__' in its name is skipped and not removed."""
        tempfile = __import__('tempfile')
        json = __import__('json')
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            # create a subdirectory whose name does NOT contain "__"
            sub = base_dir / "singletraj"
            sub.mkdir()
            # create a .traj file inside to ensure processing would happen if the name check weren't present
            traj_file = sub / "example.traj"
            traj_file.write_text(json.dumps({"info": {"submission": None}}))
            # Call with dry_run=False so remove_unfinished would remove if it considered the directory.
            remove_unfinished(base_dir, dry_run=False)
            # The directory should still exist because its name does not contain "__"
            self.assertTrue(sub.exists())
