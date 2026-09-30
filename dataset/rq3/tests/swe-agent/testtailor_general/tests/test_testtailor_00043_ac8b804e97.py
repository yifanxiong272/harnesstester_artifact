import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run._progress')
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
        """Verify on_uncaught_exception records the exception type as an exit status."""
        mgr = RunBatchProgressManager(num_instances=1)
        instance_id = "inst1"
        # start the instance so there is a spinner task to remove later
        mgr.on_instance_start(instance_id)

        # trigger an uncaught exception handling
        exc = RuntimeError("boom")
        mgr.on_uncaught_exception(instance_id, exc)

        # the exit status should record the Uncaught <ExceptionName>
        status_key = "Uncaught RuntimeError"
        self.assertIn(status_key, mgr._instances_by_exit_status)
        self.assertEqual(mgr._instances_by_exit_status[status_key], [instance_id])

        # n_completed should reflect the ended instance
        self.assertEqual(mgr.n_completed, 1)
