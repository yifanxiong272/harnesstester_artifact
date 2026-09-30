import logging
import types
import builtins
import pytest

import sweagent.run.run_batch as rb

# Helper objects used by the dummy executor and test instance
class DummyFuture:
    def __init__(self, fn, args, kwargs):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self._ran = False

    def result(self):
        # Execute the submitted function when result() is called to mimic real futures
        self._ran = True
        return self.fn(*self.args, **self.kwargs)


class DummyExecutor:
    def __init__(self, record):
        # record is a dict used to observe shutdown calls
        self._futures = []
        self.record = record

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # behave like normal context manager
        return False

    def submit(self, fn, *args, **kwargs):
        f = DummyFuture(fn, args, kwargs)
        self._futures.append(f)
        return f

    def shutdown(self, wait=True, cancel_futures=False):
        # record the shutdown call for assertions
        self.record['shutdown_called'] = True
        self.record['shutdown_wait'] = wait
        self.record['shutdown_cancel_futures'] = cancel_futures


class DummyLive:
    # Simple context manager replacement for rich.live.Live
    def __init__(self, render_group):
        self.render_group = render_group

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyLogger:
    def __init__(self):
        self.levels = []
        self.infos = []
        self.set_levels = []

    def setLevel(self, level):
        # record levels set
        self.set_levels.append(level)

    def info(self, msg):
        self.infos.append(msg)


class DummyProgressManager:
    def __init__(self):
        self.render_group = object()
        self.printed = False

    def print_report(self):
        self.printed = True


def setup_module_level_patches(monkeypatch, executor_record):
    # Patch functions and classes in the module under test to avoid side effects
    monkeypatch.setattr(rb, 'add_logger_names_to_stream_handlers', lambda: None)
    monkeypatch.setattr(rb, 'set_stream_handler_levels', lambda lvl: None)
    # Ensure logging.TRACE exists to avoid AttributeError during setLevel
    if not hasattr(logging, 'TRACE'):
        monkeypatch.setattr(logging, 'TRACE', 5)
    # Patch Live to our dummy context manager
    monkeypatch.setattr(rb, 'Live', DummyLive)
    # Patch ThreadPoolExecutor to our dummy that records shutdown calls
    monkeypatch.setattr(rb, 'ThreadPoolExecutor', lambda max_workers: DummyExecutor(executor_record))


def test_main_multi_worker_success_round_033(monkeypatch):
    """
    Scenario: All futures complete successfully. Verify print_report is called and no
    executor.shutdown with cancel_futures occurs.
    """
    executor_record = {}
    setup_module_level_patches(monkeypatch, executor_record)

    # as_completed should iterate over the futures produced by the DummyExecutor
    # Our as_completed simply returns the iterable it receives - deterministic order
    monkeypatch.setattr(rb, 'as_completed', lambda futures: iter(futures))

    # Prepare a dummy "self" with attributes used by main_multi_worker
    dummy = types.SimpleNamespace()
    dummy.logger = DummyLogger()
    dummy._progress_manager = DummyProgressManager()
    dummy._num_workers = 2

    # Create run_instance that returns identifiable values for testing
    calls = []

    def run_instance(instance):
        calls.append(('run', instance))
        return f'done-{instance}'

    dummy.run_instance = run_instance
    # Two instances to be submitted
    dummy.instances = ["a", "b"]

    # Call the unbound function as a method
    rb.RunBatch.main_multi_worker(dummy)

    # Assertions: run_instance was called for both instances via futures
    assert calls == [('run', 'a'), ('run', 'b')]
    # No shutdown with cancel_futures should have occurred
    assert executor_record.get('shutdown_called', False) is False
    # print_report must be called in finally
    assert dummy._progress_manager.printed is True


def test_main_multi_worker_keyboardinterrupt_round_033(monkeypatch):
    """
    Scenario: A future raises KeyboardInterrupt when result() is called. The code
    should catch it, log the message, call executor.shutdown(wait=False, cancel_futures=True),
    and still call print_report.
    """
    executor_record = {}
    setup_module_level_patches(monkeypatch, executor_record)

    # as_completed yields futures in order
    monkeypatch.setattr(rb, 'as_completed', lambda futures: iter(futures))

    dummy = types.SimpleNamespace()
    dummy.logger = DummyLogger()
    dummy._progress_manager = DummyProgressManager()
    dummy._num_workers = 1

    # Make run_instance raise KeyboardInterrupt for the first (and only) instance
    def run_instance(instance):
        raise KeyboardInterrupt()

    dummy.run_instance = run_instance
    dummy.instances = [42]

    rb.RunBatch.main_multi_worker(dummy)

    # Ensure the logger.info got the expected substring from the except branch message
    # The exact message is constructed across two string literals; check for key phrase
    infos = dummy.logger.infos
    assert any('Received keyboard interrupt' in m for m in infos), f"Expected keyboard interrupt log, got {infos}"

    # executor.shutdown should have been called with wait=False and cancel_futures=True
    assert executor_record.get('shutdown_called', False) is True
    assert executor_record.get('shutdown_wait') is False
    assert executor_record.get('shutdown_cancel_futures') is True

    # print_report should still be called in finally
    assert dummy._progress_manager.printed is True
