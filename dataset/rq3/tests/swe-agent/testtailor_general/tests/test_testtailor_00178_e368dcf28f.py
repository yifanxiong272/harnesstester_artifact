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
        """Ensure main constructs the app and calls its run() method with a valid trajectory path."""
        # Prepare a temporary directory (in the current working directory) with a single .traj file
        td_path = Path.cwd() / "tmp_test_traj_dir_for_main_test"
        # Clean up any previous run
        try:
            if td_path.exists():
                shutil.rmtree(td_path)
            td_path.mkdir()
            traj_file = td_path / "sample.traj"
            traj_file.write_text(
                json.dumps(
                    {
                        "info": {
                            "exit_status": "ok",
                            "model_stats": {"api_calls": 0, "instance_cost": 0},
                        }
                    }
                )
            )

            # Spy on TrajectoryInspectorApp.run to avoid launching the real UI loop
            original_run = TrajectoryInspectorApp.run
            called = []

            def run_spy(self):
                called.append(True)

            try:
                TrajectoryInspectorApp.run = run_spy
                # Call main with the temporary directory path as argument
                main([str(td_path)])
            finally:
                TrajectoryInspectorApp.run = original_run
        finally:
            # Cleanup the temporary directory if possible
            try:
                if td_path.exists():
                    shutil.rmtree(td_path)
            except Exception:
                pass

        # Verify our run spy was invoked exactly once
        self.assertEqual(len(called), 1)
