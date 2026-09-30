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
        """Trajectory missing 'replay_config' should raise the expected ValueError."""
        # Create a temporary trajectory file that does NOT contain "replay_config"
        tf = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        try:
            traj_path = Path(tf.name)
            tf.write(json.dumps({"history": []}))
            tf.flush()
            tf.close()

            with tempfile.TemporaryDirectory() as outdir:
                # Build a RunReplayConfig that points to our temp trajectory and has no deployment
                cfg = RunReplayConfig(
                    traj_path=traj_path,
                    deployment=None,
                    output_dir=Path(outdir),
                )

                expected_msg = r"Replay config not found in trajectory. Are you running on an old trajectory\?"
                with self.assertRaisesRegex(ValueError, expected_msg):
                    # This should raise while initializing RunReplay/from_config because
                    # the trajectory lacks "replay_config"
                    RunReplay.from_config(cfg)
        finally:
            try:
                traj_path.unlink()
            except Exception:
                pass
