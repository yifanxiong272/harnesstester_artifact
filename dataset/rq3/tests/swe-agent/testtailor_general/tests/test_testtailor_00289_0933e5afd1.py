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
        """When continuous_submission_every is 0, on_instance_completed should return immediately
        and not modify last_evaluation_time or spawn any subprocesses."""
        output_dir = Path("tmp_sb_eval_dir")
        output_dir.mkdir(exist_ok=True)
        try:
            sb_eval = SweBenchEvaluate(output_dir=output_dir, subset="lite", split="val", continuous_submission_every=0)

            initial_last = sb_eval.last_evaluation_time
            # result value/type doesn't matter for this early-return path
            sb_eval.on_instance_completed(result=None)

            # should have returned early: last_evaluation_time unchanged and no running calls started
            self.assertEqual(sb_eval.last_evaluation_time, initial_last)
            self.assertListEqual(sb_eval._running_calls, [])
        finally:
            # best-effort cleanup
            try:
                output_dir.rmdir()
            except Exception:
                pass
