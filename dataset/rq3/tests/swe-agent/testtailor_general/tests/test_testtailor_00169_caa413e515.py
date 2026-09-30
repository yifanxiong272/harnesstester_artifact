import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.quick_stats')
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
        """Run run_from_cli with a temporary directory containing one .traj file and
        assert the printed output contains the exit status and is not empty.
        """
        # import modules locally to avoid top-level imports
        json = __import__("json")
        tempfile = __import__("tempfile")
        pathlib = __import__("pathlib")
        io = __import__("io")
        contextlib = __import__("contextlib")
        mod = __import__("sweagent.run.quick_stats", fromlist=["run_from_cli"])
        run_from_cli = getattr(mod, "run_from_cli")

        Path = pathlib.Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            traj_file = tmp_path / "sample.traj"

            # Create a minimal valid .traj file
            traj_data = {"info": {"model_stats": {"api_calls": 5}, "exit_status": "success"}}
            traj_file.write_text(json.dumps(traj_data))

            # Capture stdout from run_from_cli
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                run_from_cli([str(tmp_path)])

            output = buf.getvalue()

            # Basic assertions about the printed result
            self.assertIn("## `success`", output)
            # Ensure some content was printed
            self.assertTrue(output.strip())
