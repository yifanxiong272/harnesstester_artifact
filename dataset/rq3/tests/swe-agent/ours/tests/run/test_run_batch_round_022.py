import types
import traceback
import pytest
from types import SimpleNamespace

import sweagent.run.run_batch as run_batch


class FakeLogger:
    def __init__(self):
        self.records = []

    def info(self, *args, **kwargs):
        self.records.append(("info", args))

    def critical(self, *args, **kwargs):
        self.records.append(("critical", args))

    def error(self, *args, **kwargs):
        self.records.append(("error", args))


class FakeProgressManager:
    def __init__(self, n_completed=0):
        self.n_completed = n_completed
        self.calls = []

    def on_instance_start(self, instance_id):
        self.calls.append(("on_instance_start", instance_id))

    def on_instance_end(self, instance_id, exit_status=None):
        self.calls.append(("on_instance_end", instance_id, exit_status))

    def on_uncaught_exception(self, instance_id, exc):
        self.calls.append(("on_uncaught_exception", instance_id, exc))

    def update_exit_status_table(self):
        self.calls.append(("update_exit_status_table",))


class DummyInstance:
    def __init__(self, id_):
        self.problem_statement = SimpleNamespace(id=id_)


# Monkeypatch module-level functions that would do real effects
run_batch.register_thread_name = lambda *_: None
run_batch.time.sleep = lambda *_: None
run_batch.random.random = lambda: 0.0


def make_self(**kwargs):
    # Provide required attributes used by run_instance
    s = SimpleNamespace()
    s.logger = kwargs.get("logger", FakeLogger())
    s._progress_manager = kwargs.get("progress_manager", FakeProgressManager())
    s._num_workers = kwargs.get("num_workers", 1)
    s._random_delay_multiplier = kwargs.get("random_delay_multiplier", 1.0)
    s._raise_exceptions = kwargs.get("raise_exceptions", False)
    # default add handler must accept keyword multi_worker
    s._add_instance_log_file_handlers = kwargs.get("add_handler", (lambda *a, **k: None))
    # remove handler usually called with a single positional arg, but accept kwargs defensively
    s._remove_instance_log_file_handlers = kwargs.get("remove_handler", (lambda *a, **k: None))
    s.should_skip = kwargs.get("should_skip", lambda instance: False)
    s._run_instance = kwargs.get("_run_instance", lambda instance: SimpleNamespace(info={}))
    return s


def test_run_instance_skipped_round_022():
    pm = FakeProgressManager(n_completed=10)
    logger = FakeLogger()
    removed = []

    def add_handler(instance_id, multi_worker=False):
        # record that add was called
        pm.calls.append(("add_handler", instance_id, multi_worker))

    def remove_handler(instance_id):
        removed.append(instance_id)

    s = make_self(logger=logger, progress_manager=pm, num_workers=4, random_delay_multiplier=1.0,
                  add_handler=add_handler, remove_handler=remove_handler,
                  should_skip=lambda instance: "already_done")

    inst = DummyInstance("inst-skip")

    # Call the bound function object with our fake self
    run_batch.RunBatch.run_instance(s, inst)

    # Assertions: on_instance_start then on_instance_end with skipped status, and handlers removed
    assert any(call[0] == "on_instance_start" and call[1] == "inst-skip" for call in pm.calls)
    assert any(call[0] == "on_instance_end" and call[1] == "inst-skip" and "skipped (already_done)" in (call[2] or "") for call in pm.calls)
    assert removed == ["inst-skip"]
    # Note: skipped branch returns before the try/finally, so update_exit_status_table is NOT expected here


def test_run_instance_systemexit_raise_true_round_022():
    pm = FakeProgressManager(n_completed=0)
    logger = FakeLogger()

    def raising_run(instance):
        raise SystemExit("bye")

    s = make_self(logger=logger, progress_manager=pm, num_workers=1,
                  _run_instance=raising_run, raise_exceptions=True,
                  remove_handler=lambda *_: None)

    inst = DummyInstance("inst-exit-true")

    with pytest.raises(SystemExit):
        run_batch.RunBatch.run_instance(s, inst)

    # even when SystemExit propagates, finally should have updated exit status table
    assert ("update_exit_status_table",) in pm.calls


def test_run_instance_systemexit_raise_false_round_022():
    pm = FakeProgressManager(n_completed=0)
    logger = FakeLogger()

    def raising_run(instance):
        raise SystemExit("bye")

    s = make_self(logger=logger, progress_manager=pm, num_workers=1,
                  _run_instance=raising_run, raise_exceptions=False,
                  remove_handler=lambda *_: None)

    inst = DummyInstance("inst-exit-false")

    # When raise_exceptions is False, the code should raise _BreakLoop instead of propagating SystemExit
    with pytest.raises(run_batch._BreakLoop):
        run_batch.RunBatch.run_instance(s, inst)

    # a critical log entry should have been recorded
    assert any(r[0] == "critical" for r in logger.records)
    assert ("update_exit_status_table",) in pm.calls


def test_run_instance_generic_exception_raise_false_round_022():
    pm = FakeProgressManager(n_completed=0)
    logger = FakeLogger()

    def raising_run(instance):
        raise RuntimeError("boom")

    removed = []
    s = make_self(logger=logger, progress_manager=pm, num_workers=1,
                  _run_instance=raising_run, raise_exceptions=False,
                  remove_handler=lambda iid: removed.append(iid))

    inst = DummyInstance("inst-generic-false")

    # Should not raise (raise_exceptions is False); should record uncaught exception and continue
    run_batch.RunBatch.run_instance(s, inst)

    # The progress manager should have recorded the uncaught exception
    assert any(call[0] == "on_uncaught_exception" and call[1] == "inst-generic-false" for call in pm.calls)
    # logger should have at least two error records (traceback + message)
    assert sum(1 for r in logger.records if r[0] == "error") >= 2
    # finally should have removed the handler and updated exit table
    assert removed == ["inst-generic-false"]
    assert ("update_exit_status_table",) in pm.calls


def test_run_instance_generic_exception_raise_true_round_022():
    pm = FakeProgressManager(n_completed=0)
    logger = FakeLogger()

    def raising_run(instance):
        raise ValueError("fatal")

    s = make_self(logger=logger, progress_manager=pm, num_workers=1,
                  _run_instance=raising_run, raise_exceptions=True,
                  remove_handler=lambda *_: None)

    inst = DummyInstance("inst-generic-true")

    with pytest.raises(ValueError):
        run_batch.RunBatch.run_instance(s, inst)

    # ensure that update_exit_status_table still runs in finally
    assert ("update_exit_status_table",) in pm.calls
