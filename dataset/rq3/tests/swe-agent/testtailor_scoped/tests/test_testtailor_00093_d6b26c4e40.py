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
        """Trigger the validator that forbids evaluate + redo_existing together."""
        # Use a plain dummy object so we don't invoke pydantic machinery.
        class Dummy:
            pass

        runcfg = Dummy()
        # Set attributes to exercise the failing branch: instances is SWEBenchInstances with evaluate=True
        runcfg.instances = SWEBenchInstances(evaluate=True)
        runcfg.redo_existing = True

        with self.assertRaises(ValueError) as cm:
            # Call the validator method directly; it only inspects attributes and raises.
            RunBatchConfig.evaluate_and_redo_existing(runcfg)

        self.assertIn(
            "Cannot evaluate and redo existing at the same time",
            str(cm.exception),
        )
