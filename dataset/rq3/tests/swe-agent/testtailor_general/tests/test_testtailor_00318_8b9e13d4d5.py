import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.hooks.swe_bench_evaluate')
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
        """Ensure on_instance_completed executes the time() assignment path and proceeds to submit when interval elapsed."""
        # Use a simple directory path (avoid needing tempfile import)
        outdir = Path("tmp_swebench_eval_out")
        outdir.mkdir(parents=True, exist_ok=True)

        # Create evaluator with a non-zero interval so the logic uses time()
        swe = SweBenchEvaluate(output_dir=outdir, subset="lite", split="dev", continuous_submission_every=1)
        # Force last_evaluation_time to be in the past so the interval has elapsed
        swe.last_evaluation_time = 0

        # Patch subprocess.Popen so we don't actually try to run sb-cli
        with unittest.mock.patch("subprocess.Popen") as mock_popen:
            mock_proc = unittest.mock.Mock()
            mock_proc.poll.return_value = None
            mock_popen.return_value = mock_proc

            # Call the hook; the result argument is unused, so a plain object is fine
            swe.on_instance_completed(result=object())

            # Confirm we attempted to start a subprocess (i.e., the code progressed past the time checks)
            mock_popen.assert_called_once()
