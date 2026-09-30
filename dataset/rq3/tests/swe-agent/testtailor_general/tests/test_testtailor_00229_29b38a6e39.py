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
        """Should log a warning and skip when multiple .traj files are present."""
        tempfile = __import__("tempfile")
        pathlib = __import__("pathlib")
        unittest_mod = __import__("unittest")
        Path = pathlib.Path

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # create a directory that matches the "__" name requirement
            subdir = base / "experiment__001"
            subdir.mkdir()
            # create two .traj files to trigger the len(trajs) > 1 branch
            (subdir / "first.traj").write_text("{}")
            (subdir / "second.traj").write_text("{}")

            # access the module-level logger used by remove_unfinished
            logger = remove_unfinished.__globals__['logger']
            with unittest_mod.mock.patch.object(logger, "warning") as mock_warn:
                # run the function under test
                remove_unfinished(base, dry_run=True)

                # verify that the specific warning for multiple trajectories was logged
                mock_warn.assert_any_call("Found multiple trajectories in %s. Skipping.", subdir)
