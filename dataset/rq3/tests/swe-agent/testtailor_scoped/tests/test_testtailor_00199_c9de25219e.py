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
        """When should_skip returns a previous exit status, run_instance should mark the
        instance as skipped and remove the instance log file handlers.
        """
        instance_id = "test_instance_skip"

        # Minimal problem statement and instance objects without relying on external imports
        class ProblemStatement:
            pass

        ps = ProblemStatement()
        ps.id = instance_id

        class Instance:
            pass

        inst = Instance()
        inst.problem_statement = ps
        inst.env = None  # not used because should_skip will short-circuit

        # Fake progress manager to record calls
        class FakeProgressManager:
            def __init__(self):
                self.n_completed = 0
                self.calls = []

            def on_instance_start(self, instance_id):
                self.calls.append(("start", instance_id))

            def on_instance_end(self, instance_id, exit_status=None):
                self.calls.append(("end", instance_id, exit_status))

            def on_uncaught_exception(self, instance_id, e):
                self.calls.append(("uncaught", instance_id, e))

            def update_exit_status_table(self):
                self.calls.append(("update_table",))

            def get_calls(self):
                return list(self.calls)

        # Simple fake logger used by RunBatch methods
        class FakeLogger:
            def info(self, *args, **kwargs):
                pass

            def error(self, *args, **kwargs):
                pass

            def critical(self, *args, **kwargs):
                pass

        # Dummy RunBatch overriding side-effectful parts
        class DummyRunBatch(RunBatch):
            def __init__(self):
                # Intentionally do not call super().__init__
                self.output_dir = "."  # not used because file handlers are overridden
                self._num_workers = 1
                self._random_delay_multiplier = 0.0
                self._raise_exceptions = False
                self.logger = FakeLogger()
                self._progress_manager = FakeProgressManager()
                self.removed_handlers = False

            def _add_instance_log_file_handlers(self, instance_id: str, multi_worker: bool = False) -> None:
                # no-op for test
                return None

            def _remove_instance_log_file_handlers(self, instance_id: str) -> None:
                # mark that removal was invoked
                self.removed_handlers = True

            def should_skip(self, instance: BatchInstance) -> str | bool:
                # Simulate that we should skip because a previous exit status exists
                return "previous_ok_status"

        rb = DummyRunBatch()

        # Execute the method under test
        rb.run_instance(inst)

        # Verify that progress manager was told the instance ended with the skipped status
        assert ("end", instance_id, "skipped (previous_ok_status)") in rb._progress_manager.get_calls()

        # Verify that we removed the instance log file handlers
        assert rb.removed_handlers is True, "Expected instance log file handlers to be removed"
