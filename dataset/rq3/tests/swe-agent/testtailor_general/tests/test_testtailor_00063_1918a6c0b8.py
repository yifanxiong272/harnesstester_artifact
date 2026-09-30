import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.rich_test')
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
        """Ensure do_task runs when Progress bars are set and updates/removes tasks."""
        run = RunBatch()

        class DummyProgress:
            def __init__(self):
                self.calls = []

            def add_task(self, description, total=None):
                self.calls.append(("add", description, total))
                return 99  # arbitrary task id

            def update(self, *args, **kwargs):
                self.calls.append(("update", args, kwargs))

            def remove_task(self, task_id):
                self.calls.append(("remove", task_id))

        main_progress = DummyProgress()
        task_progress = DummyProgress()

        run._main_progress_bar = main_progress
        run._task_progress_bar = task_progress

        # Patch the module-level time.sleep and random to avoid actual sleeping and make timings deterministic.
        mod = __import__("sys").modules[RunBatch.__module__]
        old_sleep = mod.time.sleep
        old_random = getattr(mod, "random")
        try:
            mod.time.sleep = lambda *_: None
            mod.random = lambda: 0.0

            # Run the task; should not block because sleeps are patched
            run.do_task(3)
        finally:
            mod.time.sleep = old_sleep
            mod.random = old_random

        # Verify spinner was added and later removed from task_progress
        call_types = [c[0] for c in task_progress.calls]
        self.assertIn("add", call_types)
        self.assertIn("remove", call_types)

        # Confirm the main progress bar was updated with advance=1
        main_updates = [c for c in main_progress.calls if c[0] == "update"]
        self.assertTrue(main_updates, "main progress should have received an update call")
        _, args, kwargs = main_updates[0]
        self.assertEqual(kwargs.get("advance"), 1)
