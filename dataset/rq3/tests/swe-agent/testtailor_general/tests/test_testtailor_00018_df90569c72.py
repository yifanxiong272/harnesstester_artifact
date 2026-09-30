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
        """Save a demo with a multiline observation and ensure header and YAML literal block are written."""
        data = {
            "action": "do_something",
            "observation": "first line\nsecond line\nthird line"
        }

        file = Path("demo_test_case_XX.yaml")
        traj_path = Path("/some/path/to/trajectory.json")

        # Ensure no leftover file
        if file.exists():
            file.unlink()

        try:
            # Call the function under test
            save_demo(data, file, traj_path)

            # Read the written file
            written = file.read_text()

            # Header checks
            self.assertTrue(
                written.startswith("# This is a demo file generated from trajectory file:\n"),
                "File should start with the demo header"
            )
            self.assertIn(str(traj_path), written, "Trajectory path should be present in the header")

            # YAML content checks: multiline string should be serialized as a literal block (|) and contain the lines
            self.assertIn("observation: |", written, "Multiline observation should be serialized as a YAML literal block")
            self.assertIn("first line", written)
            self.assertIn("second line", written)
            self.assertIn("third line", written)
        finally:
            # Clean up
            if file.exists():
                file.unlink()
