import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.run_replay')
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
        """Model should replace the DEFAULT output_dir with a trajectories path and create it."""
        # create a RunReplayConfig with the default output_dir (Path("DEFAULT"))
        traj_path = Path("example_repo/some_traj.yaml")
        cfg = RunReplayConfig(traj_path=traj_path)

        # If pydantic did not run model_post_init automatically, run it explicitly.
        if cfg.output_dir == Path("DEFAULT"):
            cfg.model_post_init(None)

        # After initialization, output_dir must have been replaced
        self.assertNotEqual(cfg.output_dir, Path("DEFAULT"))

        # The final directory name should include the trajectory stem
        expected_name = f"replay___{cfg.traj_path.stem}"
        self.assertEqual(cfg.output_dir.name, expected_name)

        # The path must include a 'trajectories' component and the directory must exist
        self.assertIn("trajectories", cfg.output_dir.parts)
        self.assertTrue(cfg.output_dir.exists())
