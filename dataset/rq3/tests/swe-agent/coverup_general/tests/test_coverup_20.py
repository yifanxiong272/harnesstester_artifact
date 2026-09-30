# file: sweagent/run/run_batch.py:291-331
# asked: {"lines": [302, 303, 305, 306, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324], "branches": [[301, 302], [315, 316], [315, 317], [323, 324], [323, 330]]}
# gained: {"lines": [302, 303, 305, 306, 312, 313, 314, 315, 317, 318, 319, 320, 321, 322, 323], "branches": [[301, 302], [315, 317], [323, 330]]}

import pytest
from types import SimpleNamespace

from sweagent.run.run_batch import RunBatch, _BreakLoop
from sweagent.exceptions import ModelConfigurationError


class DummyLogger:
    def __init__(self):
        self.infos = []
        self.criticals = []
        self.errors = []

    def info(self, *args, **kwargs):
        self.infos.append((args, kwargs))

    def critical(self, *args, **kwargs):
        self.criticals.append((args, kwargs))

    def error(self, *args, **kwargs):
        self.errors.append((args, kwargs))


class DummyProgressManager:
    def __init__(self, n_completed=1):
        self.n_completed = n_completed
        self.started = []
        self.ended = []
        self.uncaught = []
        self.updated = False

    def on_instance_start(self, instance_id):
        self.started.append(instance_id)

    def on_instance_end(self, instance_id, exit_status=None):
        self.ended.append((instance_id, exit_status))

    def on_uncaught_exception(self, instance_id, exc):
        self.uncaught.append((instance_id, exc))

    def update_exit_status_table(self):
        self.updated = True


def make_runbatch(monkeypatch, *, n_completed=1):
    rb = object.__new__(RunBatch)
    rb.logger = DummyLogger()
    rb._num_workers = 1
    rb._random_delay_multiplier = 0.0
    rb._raise_exceptions = False
    rb._progress_manager = DummyProgressManager(n_completed=n_completed)
    rb._add_calls = []
    rb._remove_calls = []

    def add_handlers(instance_id, multi_worker=False):
        rb._add_calls.append((instance_id, multi_worker))

    def remove_handlers(instance_id):
        rb._remove_calls.append(instance_id)

    rb._add_instance_log_file_handlers = add_handlers
    rb._remove_instance_log_file_handlers = remove_handlers

    return rb


def make_instance(instance_id="iid"):
    return SimpleNamespace(problem_statement=SimpleNamespace(id=instance_id))


def test_run_instance_skipped(monkeypatch):
    rb = make_runbatch(monkeypatch)
    inst = make_instance("skip-me")

    # should_skip returns truthy status string
    rb.should_skip = lambda instance: "already_done"

    # Ensure _run_instance would not be called accidentally
    rb._run_instance = lambda instance: (_ for _ in ()).throw(RuntimeError("should not run"))

    # Call
    result = rb.run_instance(inst)

    # Since skipped, result is None and on_instance_end was called with the skipped message
    assert result is None
    assert rb._progress_manager.ended == [("skip-me", "skipped (already_done)")]
    # Handlers should have been added then removed by the skip branch
    assert rb._add_calls == [("skip-me", False)]
    assert rb._remove_calls == ["skip-me"]
    # Because skip path returns early, update_exit_status_table should NOT have been called
    assert rb._progress_manager.updated is False


def test_run_instance_keyboardinterrupt_raises_breakloop(monkeypatch):
    rb = make_runbatch(monkeypatch)
    inst = make_instance("kb")

    rb.should_skip = lambda instance: False

    # _run_instance raises KeyboardInterrupt
    def raising(instance):
        raise KeyboardInterrupt

    rb._run_instance = raising

    with pytest.raises(_BreakLoop):
        rb.run_instance(inst)

    # add handlers should have been called
    assert rb._add_calls == [("kb", False)]
    # finally should have updated exit status table and removed handlers
    assert rb._progress_manager.updated is True
    assert rb._remove_calls == ["kb"]


def test_run_instance_modelconfigerror_non_raise_logs_and_breaks(monkeypatch):
    rb = make_runbatch(monkeypatch)
    inst = make_instance("mce")

    rb.should_skip = lambda instance: False

    def raising(instance):
        raise ModelConfigurationError("bad config")

    rb._run_instance = raising
    rb._raise_exceptions = False

    with pytest.raises(_BreakLoop):
        rb.run_instance(inst)

    # logger.critical should have been called
    assert rb.logger.criticals, "expected a critical log for ModelConfigurationError"
    # finally should have updated and removed
    assert rb._progress_manager.updated is True
    assert rb._remove_calls == ["mce"]


def test_run_instance_generic_exception_logs_and_continues(monkeypatch):
    rb = make_runbatch(monkeypatch)
    inst = make_instance("boom")

    rb.should_skip = lambda instance: False

    def raising(instance):
        raise RuntimeError("boom")

    rb._run_instance = raising
    rb._raise_exceptions = False

    # Should not raise because _raise_exceptions is False; instead it should log and continue
    result = rb.run_instance(inst)
    assert result is None

    # Check that errors were logged (traceback + message)
    assert rb.logger.errors, "expected error logs for generic exception"
    # Progress manager should have recorded the uncaught exception
    assert len(rb._progress_manager.uncaught) == 1
    inst_id, exc = rb._progress_manager.uncaught[0]
    assert inst_id == "boom"
    assert isinstance(exc, Exception)
    assert "boom" in str(exc)

    # finally should have updated and removed handlers
    assert rb._progress_manager.updated is True
    assert rb._remove_calls == ["boom"]
