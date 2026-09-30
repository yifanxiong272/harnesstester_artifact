import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.run_batch')
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
        """Validate that the RunBatchConfig validator returns successfully for SWE-Bench instances
        when evaluate and redo_existing are not both true (covers the final `return self` path).
        """
        cfg = RunBatchConfig.model_validate(
            {
                "instances": {
                    "type": "swe_bench",
                    "subset": "lite",
                    "split": "dev",
                    "evaluate": False,
                },
                "agent": {"model": {"name": "instant_empty_submit"}},
            }
        )
        self.assertIsInstance(cfg, RunBatchConfig)
        self.assertIsInstance(cfg.instances, SWEBenchInstances)
