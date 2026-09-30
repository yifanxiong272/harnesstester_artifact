import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.data_science.proposal.exp_gen.select.submit')
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
        """Test that process_experiment logs an error when loop_id is None and proceeds safely."""
        # Prepare a minimal DSExperiment with a main.py so workspace injection is plausible
        exp = DSExperiment(pending_tasks_list=[])
        exp.experiment_workspace.file_dict = {"main.py": "print('hello')"}

        # Fake result and workspace to avoid heavy environment interaction
        class FakeResult:
            def __init__(self, exit_code=1):
                self.exit_code = exit_code

            def get_truncated_stdout(self):
                return ""

        class FakeWS:
            def __init__(self, *args, **kwargs):
                self.file_dict = {}

            def inject_code_from_file_dict(self, workspace):
                # mimic accepting workspace injection
                self.injected = True

            # Accept keyword args as process_experiment calls ws.run(env=..., entry=...)
            def run(self, *args, **kwargs):
                # return non-zero exit code to skip grading branch
                return FakeResult(exit_code=1)

        # Create a fake T callable that returns an object with r() method
        FakeTObj = type("TObj", (), {"r": lambda self: "input_folder"})

        # Minimal DS_RD_SETTING-like object
        FakeDSRD = type("S", (), {"full_timeout": 1, "debug_timeout": 1})()

        # Mock logger to capture error call
        fake_logger = MagicMock()

        # Patch the globals used inside process_experiment to use fakes
        patch_values = {
            "FBWorkspace": FakeWS,
            "get_ds_env": lambda *a, **k: object(),
            "T": lambda *a, **k: FakeTObj(),
            "logger": fake_logger,
            "DS_RD_SETTING": FakeDSRD,
        }

        with patch.dict(process_experiment.__globals__, patch_values):
            result = process_experiment(exp, competition="comp", folder="folder", grade_py_code="grade", loop_id=None)

        # Ensure logger.error was called due to loop_id being None
        fake_logger.error.assert_called()
        err_args = fake_logger.error.call_args[0]
        self.assertIn("Could not find loop_id for a given experiment.", err_args[0])

        # Check the function returned the experiment and None scores (since we returned non-zero exit)
        self.assertIs(result[0], exp)
        self.assertIsNone(result[1])
        self.assertIsNone(result[2])
