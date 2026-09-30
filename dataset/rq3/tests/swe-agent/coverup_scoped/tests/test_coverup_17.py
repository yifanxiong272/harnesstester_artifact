# file: sweagent/run/run_batch.py:268-289
# asked: {"lines": [269, 272, 273, 275, 276, 277, 278, 279, 280, 281, 282, 283, 286, 287, 289], "branches": [[279, 280], [279, 289]]}
# gained: {"lines": [269, 272, 273, 275, 276, 277, 278, 279, 280, 281, 282, 283, 286, 287, 289], "branches": [[279, 280], [279, 289]]}

import logging
import types
import pytest

import sweagent.run.run_batch as run_batch_module
from sweagent.run.run_batch import RunBatch


class DummyLogger:
    def __init__(self):
        self.set_levels = []
        self.infos = []

    def setLevel(self, lvl):
        self.set_levels.append(lvl)

    def info(self, msg):
        self.infos.append(msg)


class DummyProgressManager:
    def __init__(self):
        self.render_group = object()
        self.print_report_called = False

    def print_report(self):
        self.print_report_called = True


class DummyLive:
    def __init__(self, render_group):
        self.render_group = render_group

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def setup_common(monkeypatch):
    # Spy replacements for module-level functions
    called = {}

    def fake_add_logger_names_to_stream_handlers():
        called['add_called'] = True

    def fake_set_stream_handler_levels(level):
        called['set_called'] = level

    monkeypatch.setattr(run_batch_module, "add_logger_names_to_stream_handlers", fake_add_logger_names_to_stream_handlers)
    monkeypatch.setattr(run_batch_module, "set_stream_handler_levels", fake_set_stream_handler_levels)

    # Ensure logging.TRACE exists for the test and is cleaned up automatically by monkeypatch
    monkeypatch.setattr(logging, "TRACE", 5, raising=False)

    # Replace Live context manager
    monkeypatch.setattr(run_batch_module, "Live", DummyLive)

    return called


def make_runbatch_instance(monkeypatch, num_instances=3, num_workers=2):
    # Create an instance without invoking original __init__
    rb = RunBatch.__new__(RunBatch)
    # Minimal attributes used by main_multi_worker
    rb.logger = DummyLogger()
    rb._progress_manager = DummyProgressManager()
    rb._num_workers = num_workers
    rb.instances = [f"inst{i}" for i in range(num_instances)]
    return rb


def test_main_multi_worker_success(monkeypatch):
    called = setup_common(monkeypatch)
    rb = make_runbatch_instance(monkeypatch, num_instances=4, num_workers=2)

    processed = []

    def run_instance_success(self, instance):
        # simulate some work
        processed.append(instance)
        return None

    rb.run_instance = types.MethodType(run_instance_success, rb)

    # Execute
    rb.main_multi_worker()

    # Assertions
    assert called.get('add_called', False) is True
    assert called.get('set_called') == logging.WARNING
    # logger.setLevel should have been called with logging.TRACE
    assert rb.logger.set_levels == [logging.TRACE]
    # All instances processed
    assert set(processed) == set(rb.instances)
    # Progress report printed
    assert rb._progress_manager.print_report_called is True


def test_main_multi_worker_keyboardinterrupt(monkeypatch):
    called = setup_common(monkeypatch)
    rb = make_runbatch_instance(monkeypatch, num_instances=3, num_workers=2)

    # run_instance will raise KeyboardInterrupt to trigger the except branch
    def run_instance_raise(self, instance):
        raise KeyboardInterrupt

    rb.run_instance = types.MethodType(run_instance_raise, rb)

    # Execute
    rb.main_multi_worker()

    # Assertions
    assert called.get('add_called', False) is True
    assert called.get('set_called') == logging.WARNING
    # logger.setLevel should have been called with logging.TRACE
    assert rb.logger.set_levels == [logging.TRACE]
    # The logger should have received the info message about keyboard interrupt
    expected_msg = "Received keyboard interrupt, waiting for running instances to finish, but cancelled everything else"
    # At least one info call with the expected message
    assert any(expected_msg == m for m in rb.logger.infos)
    # Progress report printed even after exception
    assert rb._progress_manager.print_report_called is True
