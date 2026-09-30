import pytest
from types import SimpleNamespace
import sweagent.run.run_batch as run_batch
from sweagent.exceptions import ModelConfigurationError

# Make thread registration a noop for deterministic tests
run_batch.register_thread_name = lambda *_: None


def _make_dummy_runbatch():
    """Create a RunBatch-like object with the minimal attributes used by run_instance.
    We instantiate without calling the real initializer and attach only the
    attributes that run_instance accesses. This keeps tests deterministic and
    side-effect free.
    """
    rb = object.__new__(run_batch.RunBatch)

    # Simple logger that records calls
    class DummyLogger:
        def __init__(self):
            self.infos = []
            self.errors = []
            self.criticals = []

        def info(self, *args, **kwargs):
            self.infos.append((args, kwargs))

        def error(self, *args, **kwargs):
            self.errors.append((args, kwargs))

        def critical(self, *args, **kwargs):
            self.criticals.append((args, kwargs))

    rb.logger = DummyLogger()

    # Track calls to add/remove handlers
    rb._removed_handlers = []
    rb._added_handlers = []
    rb._add_instance_log_file_handlers = lambda instance_id, multi_worker=False: rb._added_handlers.append((instance_id, multi_worker))
    rb._remove_instance_log_file_handlers = lambda instance_id: rb._removed_handlers.append(instance_id)

    # Progress manager mock
    class DummyProgress:
        def __init__(self):
            self.n_completed = 1
            self.start_calls = []
            self.end_calls = []
            self.uncaught = []
            self.updated = 0

        def on_instance_start(self, instance_id):
            self.start_calls.append(instance_id)

        def on_instance_end(self, instance_id, exit_status=None):
            self.end_calls.append((instance_id, exit_status))

        def on_uncaught_exception(self, instance_id, exc):
            self.uncaught.append((instance_id, exc))

        def update_exit_status_table(self):
            self.updated += 1

    rb._progress_manager = DummyProgress()

    # Default attributes to avoid sleeps and multi-worker behavior
    rb._num_workers = 1
    rb._random_delay_multiplier = 0.0

    # Flags and callables to be set by individual tests
    rb.should_skip = lambda instance: False
    rb._run_instance = lambda instance: SimpleNamespace(info={})
    rb._raise_exceptions = False

    return rb


def _make_instance(instance_id="inst-1"):
    return SimpleNamespace(problem_statement=SimpleNamespace(id=instance_id))


def test_should_skip_round_024():
    rb = _make_dummy_runbatch()
    instance = _make_instance("skip-me")

    # should_skip returns a truthy previous exit status -> early skip path
    rb.should_skip = lambda inst: "already_done"

    # Call run_instance
    rb.run_instance(instance)

    # Assertions: the progress manager should be told that the instance ended with skipped(status)
    assert rb._progress_manager.end_calls, "on_instance_end should have been called"
    assert rb._progress_manager.end_calls[-1][0] == "skip-me"
    assert "skipped (already_done)" in rb._progress_manager.end_calls[-1][1]

    # The log-file handlers should have been removed in the skip path
    assert rb._removed_handlers.count("skip-me") >= 1

    # Note: in the skip path the function returns before the try/finally block, so
    # update_exit_status_table is NOT called. Assert that it was not called.
    assert rb._progress_manager.updated == 0


def test_keyboardinterrupt_raises_breakloop_round_024():
    rb = _make_dummy_runbatch()
    instance = _make_instance("kb-exc")

    # Make _run_instance raise KeyboardInterrupt
    def raise_ki(inst):
        raise KeyboardInterrupt

    rb.should_skip = lambda inst: False
    rb._run_instance = raise_ki

    with pytest.raises(run_batch._BreakLoop):
        rb.run_instance(instance)

    # Ensure lifecycle hooks were invoked (start) and finally ran (update)
    assert rb._progress_manager.start_calls == ["kb-exc"]
    assert rb._progress_manager.updated >= 1
    assert "kb-exc" in rb._removed_handlers


def test_systemexit_with_raise_true_re_raises_round_024():
    rb = _make_dummy_runbatch()
    instance = _make_instance("sys-exit")

    rb.should_skip = lambda inst: False

    def raise_sys(inst):
        raise SystemExit("stop")

    rb._run_instance = raise_sys
    rb._raise_exceptions = True

    with pytest.raises(SystemExit):
        rb.run_instance(instance)

    # finally should still run
    assert rb._progress_manager.updated >= 1


def test_modelconfig_error_with_raise_false_turns_into_breakloop_round_024():
    rb = _make_dummy_runbatch()
    instance = _make_instance("modelcfg")

    rb.should_skip = lambda inst: False

    def raise_modelcfg(inst):
        raise ModelConfigurationError("bad config")

    rb._run_instance = raise_modelcfg
    rb._raise_exceptions = False

    with pytest.raises(run_batch._BreakLoop):
        rb.run_instance(instance)

    # Ensure critical was logged about the class name
    crits = rb.logger.criticals
    assert crits, "expected a critical log entry"
    # The message should mention the exception class name
    found = any("ModelConfigurationError" in str(args) for (args, _) in crits)
    assert found, "critical log should mention ModelConfigurationError"

    # finally ran
    assert rb._progress_manager.updated >= 1


def test_general_exception_with_raise_false_records_uncaught_round_024():
    rb = _make_dummy_runbatch()
    instance = _make_instance("gen-exc")

    rb.should_skip = lambda inst: False

    def raise_val(inst):
        raise ValueError("oops")

    rb._run_instance = raise_val
    rb._raise_exceptions = False

    # Should not re-raise; instead the uncaught handler should be invoked
    rb.run_instance(instance)

    assert rb._progress_manager.uncaught, "on_uncaught_exception should have been called"
    assert rb._progress_manager.uncaught[-1][0] == "gen-exc"
    assert isinstance(rb._progress_manager.uncaught[-1][1], ValueError)
    # finally ran
    assert rb._progress_manager.updated >= 1


def test_general_exception_with_raise_true_re_raises_round_024():
    rb = _make_dummy_runbatch()
    instance = _make_instance("gen-exc-raise")

    rb.should_skip = lambda inst: False

    def raise_val(inst):
        raise ValueError("boom")

    rb._run_instance = raise_val
    rb._raise_exceptions = True

    with pytest.raises(ValueError):
        rb.run_instance(instance)

    # finally should still run
    assert rb._progress_manager.updated >= 1
