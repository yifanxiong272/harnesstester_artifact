import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.run_traj_to_demo')
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
        """Test that main builds the expected output path and writes the demo file."""
        tempfile = __import__("tempfile")
        pathlib = __import__("pathlib")
        json = __import__("json")
        Path = pathlib.Path

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            # Create a trajectory directory and file with minimal valid content
            traj_dir = tmpdir / "sessionA"
            traj_dir.mkdir()
            traj_path = traj_dir / "example.traj"
            traj_content = {
                "replay_config": {"speed": 1},
                "history": [
                    {"role": "assistant", "content": "action1", "agent": "main"},
                    {"role": "user", "content": "should be filtered", "agent": "main"},
                    {"role": "assistant", "content": "action2", "agent": "primary", "is_demo": False},
                ],
            }
            traj_path.write_text(json.dumps(traj_content))

            output_dir = tmpdir / "out"
            # Call main to produce the demo file with a suffix
            suffix = "_suf"
            main(traj_path, output_dir, suffix=suffix, overwrite=False, include_user=False)

            # Expected output file path per the target line in the function under test
            expected_output_file = output_dir / (traj_path.parent.name + suffix) / (
                traj_path.stem.removesuffix(".traj") + ".demo.yaml"
            )

            # Assertions: file exists and contains header and trajectory path
            self.assertTrue(expected_output_file.exists(), f"Expected demo file at {expected_output_file} not found")
            content = expected_output_file.read_text()
            self.assertIn("This is a demo file generated from trajectory file:", content)
            self.assertIn(str(traj_path), content)
