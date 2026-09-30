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
        """Verify that _get_sb_call builds the expected sb-cli call for both submit_only False and True."""
        # Prepare object with known parameters
        output_dir = Path("my_output_dir")
        subset = "lite"
        split = "validation"
        swe = SweBenchEvaluate(output_dir=output_dir, subset=subset, split=split)

        preds_path = Path("preds.json")

        # Call with submit_only = False (default)
        args = swe._get_sb_call(preds_path=preds_path, submit_only=False)

        expected_base = [
            "sb-cli",
            "submit",
            swe._SUBSET_MAP[subset],
            split,
            "--predictions_path",
            str(preds_path),
            "--run_id",
            swe.run_id,
            "--output_dir",
            str(output_dir / "sb-cli-reports"),
        ]
        self.assertEqual(args, expected_base)

        # Call with submit_only = True -> extra flags appended
        args_submit_only = swe._get_sb_call(preds_path=preds_path, submit_only=True)
        expected_submit_only = expected_base + ["--wait_for_evaluation", "0", "--gen_report", "0", "--verify_submission", "0"]
        self.assertEqual(args_submit_only, expected_submit_only)
