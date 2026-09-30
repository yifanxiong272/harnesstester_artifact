# file: sweagent/run/run_batch.py:268-289
# asked: {"lines": [269, 272, 273, 275, 276, 277, 278, 279, 280, 281, 282, 283, 286, 287, 289], "branches": [[279, 280], [279, 289]]}
# gained: {"lines": [269, 272, 273, 275, 276, 277, 278, 279, 280, 281, 282, 283, 286, 287, 289], "branches": [[279, 280], [279, 289]]}

import logging
import types

import pytest

from sweagent.run import run_batch


class _Flag:
    def __init__(self):
        self.value = False


class FakeLogger:
    def __init__(self):
        self.set_level_args = None
        self.info_calls = []

    def setLevel(self, arg):
        self.set_level_args = arg

    def info(self, msg):
        self.info_calls.append(msg)


class FakeProgressManager:
    def __init__(self):
        self.render_group = object()
        self.printed = _Flag()

    def print_report(self):
        self.printed.value = True


class DummyLive:
    def __init__(self, arg):
        self.arg = arg
        self.entered = _Flag()
        self.exited = _Flag()

    def __enter__(self):
        self.entered.value = True
        return self

    def __exit__(self, exc_type, exc, tb):
        self.exited.value = True
        return False


class FakeFuture:
    def __init__(self, func, arg):
        self.func = func
        self.arg = arg
        self._ran = False

    def result(self):
        self._ran = True
        return self.func(self.arg)


class FakeExecutor:
    def __init__(self, max_workers=None):
        self.max_workers = max_workers
        self.submissions = []
        self.shutdown_called = _Flag()
        self.shutdown_args = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def submit(self, func, arg):
        fut = FakeFuture(func, arg)
        self.submissions.append((func, arg, fut))
        return fut

    def shutdown(self, wait=True, cancel_futures=False):
        self.shutdown_called.value = True
        self.shutdown_args = {"wait": wait, "cancel_futures": cancel_futures}


def make_runbatch_instance(run_instance_impl, instances, logger=None, progress_manager=None, num_workers=2):
    # Create a RunBatch instance without calling its __init__
    rb = object.__new__(run_batch.RunBatch)
    rb.logger = logger or FakeLogger()
    rb._progress_manager = progress_manager or FakeProgressManager()
    rb._num_workers = num_workers
    rb.instances = list(instances)
    rb.run_instance = types.MethodType(run_instance_impl, rb)
    return rb


def test_main_multi_worker_normal_completion(monkeypatch):
    # Ensure logging.TRACE exists for the module code
    monkeypatch.setattr(logging, "TRACE", 5, raising=False)

    called_add = _Flag()
    called_set_levels = {"called": False, "level": None}

    def fake_add_loggers():
        called_add.value = True

    def fake_set_levels(level):
        called_set_levels["called"] = True
        called_set_levels["level"] = level

    # Patch module-level functions and classes
    monkeypatch.setattr(run_batch, "add_logger_names_to_stream_handlers", fake_add_loggers)
    monkeypatch.setattr(run_batch, "set_stream_handler_levels", fake_set_levels)
    monkeypatch.setattr(run_batch, "Live", DummyLive)
    monkeypatch.setattr(run_batch, "ThreadPoolExecutor", FakeExecutor)
    monkeypatch.setattr(run_batch, "as_completed", lambda futures: iter(futures))

    # Define a run_instance that always succeeds
    def run_instance(self, instance):
        return f"ran-{instance}"

    prog = FakeProgressManager()
    logger = FakeLogger()
    rb = make_runbatch_instance(run_instance, instances=["one", "two"], logger=logger, progress_manager=prog, num_workers=2)

    # Execute
    rb.main_multi_worker()

    # Assertions: functions called and final report printed, no info logs (no exception)
    assert called_add.value is True
    assert called_set_levels["called"] is True
    assert called_set_levels["level"] == logging.WARNING
    assert logger.set_level_args == logging.TRACE
    assert prog.printed.value is True
    assert logger.info_calls == []


def test_main_multi_worker_keyboard_interrupt(monkeypatch):
    # Ensure logging.TRACE exists for the module code
    monkeypatch.setattr(logging, "TRACE", 5, raising=False)

    called_add = _Flag()
    called_set_levels = {"called": False, "level": None}

    def fake_add_loggers():
        called_add.value = True

    def fake_set_levels(level):
        called_set_levels["called"] = True
        called_set_levels["level"] = level

    # Patch module-level functions and classes
    monkeypatch.setattr(run_batch, "add_logger_names_to_stream_handlers", fake_add_loggers)
    monkeypatch.setattr(run_batch, "set_stream_handler_levels", fake_set_levels)
    monkeypatch.setattr(run_batch, "Live", DummyLive)

    # We'll capture the executor instance used by the function
    executor_holder = {}

    def FakeExecutorCapture(max_workers=None):
        ex = FakeExecutor(max_workers=max_workers)
        executor_holder["executor"] = ex
        return ex

    monkeypatch.setattr(run_batch, "ThreadPoolExecutor", FakeExecutorCapture)
    monkeypatch.setattr(run_batch, "as_completed", lambda futures: iter(futures))

    # Define a run_instance that raises KeyboardInterrupt for a specific instance
    def run_instance(self, instance):
        if instance == "boom":
            raise KeyboardInterrupt("simulated")
        return f"ran-{instance}"

    prog = FakeProgressManager()
    logger = FakeLogger()
    rb = make_runbatch_instance(run_instance, instances=["ok", "boom", "later"], logger=logger, progress_manager=prog, num_workers=3)

    # Execute - should catch KeyboardInterrupt from one of the futures
    rb.main_multi_worker()

    # Assertions: functions called, info logged, executor.shutdown called with expected args, and final report printed
    assert called_add.value is True
    assert called_set_levels["called"] is True
    assert called_set_levels["level"] == logging.WARNING
    assert logger.set_level_args == logging.TRACE

    # Check that logger.info was called with the expected message
    expected_msg = "Received keyboard interrupt, waiting for running instances to finish, but cancelled everything else"
    assert any(expected_msg in m for m in logger.info_calls), f"info calls: {logger.info_calls}"

    # Executor shutdown should have been called with wait=False, cancel_futures=True
    executor = executor_holder.get("executor")
    assert executor is not None, "executor was not created"
    assert executor.shutdown_called.value is True
    assert executor.shutdown_args == {"wait": False, "cancel_futures": True}

    # Progress printed
    assert prog.printed.value is True
