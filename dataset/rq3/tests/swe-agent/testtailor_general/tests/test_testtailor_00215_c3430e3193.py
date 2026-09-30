import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.inspector_cli')
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
        """Verify TrajectoryViewer.__init__ sets internal state from the given path and args."""
        # Prepare a JSON trajectory file using Path.write_text to avoid needing tempfile/os imports
        content = {
            "trajectory": [
                {"thought": "t", "action": "a", "observation": "o"}
            ],
            "info": {}
        }
        p = Path("tmp_test_traj.json")
        try:
            p.write_text(json.dumps(content))

            viewer = TrajectoryViewer(p, "MyTitle", {"result": "passed"}, gold_patch="gpatch")

            # Check that __init__ initialized fields as expected
            self.assertEqual(viewer.i_step, -1)
            self.assertEqual(viewer.trajectory, content)
            self.assertFalse(viewer.show_full)
            self.assertEqual(viewer.title, "MyTitle")
            self.assertEqual(viewer.overview_stats, {"result": "passed"})
            self.assertEqual(viewer.gold_patch, "gpatch")

            # n_steps should reflect the trajectory length
            self.assertEqual(viewer.n_steps, 1)
        finally:
            # Cleanup the file if it exists
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass
