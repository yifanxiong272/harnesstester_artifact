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
        """Write a small trajectory file and ensure convert_traj_to_action_demo reads it and writes a demo file
        that contains only the assistant actions (and the replay_config parsed from a JSON-string)."""
        # Use __import__ to avoid top-level import statements in this submission
        tempfile = __import__("tempfile")
        json = __import__("json")
        pathlib = __import__("pathlib")
        Path = pathlib.Path

        with tempfile.TemporaryDirectory() as tmpdir:
            traj_path = Path(tmpdir) / "traj.json"
            output_path = Path(tmpdir) / "demo.yaml"

            traj = {
                # replay_config as a JSON-encoded string to exercise the isinstance -> json.loads branch
                "replay_config": json.dumps({"foo": "bar"}),
                "history": [
                    # should be kept: assistant, main
                    {"role": "assistant", "content": "assistant says hello", "agent": "main"},
                    # should be filtered out because role is user and include_user=False
                    {"role": "user", "content": "user says hi", "agent": "main"},
                    # should be filtered out because agent is not main/primary
                    {"role": "assistant", "content": "assistant from secondary", "agent": "secondary"},
                    # should be filtered out because is_demo is True
                    {"role": "assistant", "content": "assistant demo", "agent": "main", "is_demo": True},
                    # tool role should be ignored (not in admissible_roles when include_user=False)
                    {"role": "tool", "content": "tool output", "agent": "main"},
                ],
            }

            with open(traj_path, "w") as f:
                json.dump(traj, f)

            # Call the function under test
            convert_traj_to_action_demo(traj_path, output_path, include_user=False)

            # Output file must exist
            self.assertTrue(output_path.exists(), "Expected demo output file to be created")

            content = output_path.read_text()

            # Header should reference the original trajectory path
            self.assertIn(str(traj_path), content)

            # The assistant main message should be present
            self.assertIn("assistant says hello", content)

            # The user message should NOT be present because include_user=False
            self.assertNotIn("user says hi", content)

            # The assistant from a non-main agent should NOT be present
            self.assertNotIn("assistant from secondary", content)

            # The is_demo assistant message should NOT be present
            self.assertNotIn("assistant demo", content)

            # replay_config should have been parsed and included (check a key:value pair in YAML)
            self.assertIn("foo: bar", content)
