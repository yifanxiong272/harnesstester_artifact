import logging
import types
import pytest
from types import SimpleNamespace

import sweagent.run.run_batch as run_batch


# Dummy objects / helpers used to avoid real UI or logging side-effects
class DummyLive:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.level_set = None

    def setLevel(self, level):
        # accept anything
        self.level_set = level

    def info(self, msg):
        self.infos.append(msg)


class ProgressManager:
    def __init__(self):
        self.render_group = None
        self.printed = False

    def print_report(self):
        self.printed = True


@pytest.fixture(autouse=True)
def patch_module(monkeypatch):
    # Replace Live context manager with a no-op to avoid rich side effects
    monkeypatch.setattr(run_batch, "Live", DummyLive)
    # No-op some logging helpers imported by the module to keep deterministic behavior
    monkeypatch.setattr(run_batch, "add_logger_names_to_stream_handlers", lambda: None)
    monkeypatch.setattr(run_batch, "set_stream_handler_levels", lambda level: None)
    # Ensure logging.TRACE exists so the attribute access in the code does not raise
    setattr(logging, "TRACE", getattr(logging, "TRACE", 5))
    yield


def test_main_multi_worker_no_exception_round_035():
    """
    Exercise the normal path of main_multi_worker where all futures complete normally.

    Assertions:
    - run_instance is invoked for each instance
    - progress manager's print_report is called in the finally block
    - logger.info is NOT called (no KeyboardInterrupt/_BreakLoop)
    """
    # Prepare a lightweight fake instance object compatible with RunBatch.main_multi_worker
    inst_obj = SimpleNamespace()
    inst_obj.instances = ["a", "b", "c"]
    inst_obj._num_workers = 2

    progress = ProgressManager()
    inst_obj._progress_manager = progress

    logger = DummyLogger()
    inst_obj.logger = logger

    # record calls
    run_calls = []

    def run_instance(instance):
        run_calls.append(instance)
        return f"done-{instance}"

    inst_obj.run_instance = run_instance

    # Call the method under test
    run_batch.RunBatch.main_multi_worker(inst_obj)

    # Assertions - observable behavior
    assert run_calls == inst_obj.instances
    assert progress.printed is True
    assert logger.infos == []


def test_main_multi_worker_keyboard_interrupt_round_035():
    """
    Exercise the exception path of main_multi_worker where one worker raises KeyboardInterrupt.

    Assertions:
    - progress manager's print_report is still called (finally block)
    - logger.info is called with the keyboard-interrupt message
    """
    inst_obj = SimpleNamespace()
    # two instances: ensure at least one completes and one raises
    inst_obj.instances = [1, 2]
    inst_obj._num_workers = 2

    progress = ProgressManager()
    inst_obj._progress_manager = progress

    logger = DummyLogger()
    inst_obj.logger = logger

    run_calls = []

    def run_instance(instance):
        run_calls.append(instance)
        if instance == 2:
            # Raise the same exception type the production code catches
            raise KeyboardInterrupt()
        return f"ok-{instance}"

    inst_obj.run_instance = run_instance

    # Execute
    run_batch.RunBatch.main_multi_worker(inst_obj)

    # Assertions
    # At least the successful instance was executed (the failing one may have raised in worker)
    assert 1 in run_calls
    # The progress manager's report must always be printed (finally clause)
    assert progress.printed is True
    # Logger must have been informed about the keyboard interrupt
    assert any("Received keyboard interrupt" in m for m in logger.infos), "expected keyboard-interrupt log"
