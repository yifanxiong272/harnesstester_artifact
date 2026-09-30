# file: sweagent/run/run_batch.py:291-331
# asked: {"lines": [302, 303, 305, 306, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324], "branches": [[301, 302], [315, 316], [315, 317], [323, 324], [323, 330]]}
# gained: {"lines": [302, 303, 305, 306, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324], "branches": [[301, 302], [315, 316], [315, 317], [323, 324], [323, 330]]}

import types
import pytest
from types import SimpleNamespace

from sweagent.run import run_batch
from sweagent.exceptions import ModelConfigurationError, TotalCostLimitExceededError


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
    def __init__(self, n_completed=0):
        self.n_completed = n_completed
        self.started = []
        self.ended = []
        self.uncaught = []
        self.updated = 0

    def on_instance_start(self, instance_id):
        self.started.append(instance_id)

    def on_instance_end(self, instance_id, exit_status):
        self.ended.append((instance_id, exit_status))

    def on_uncaught_exception(self, instance_id, exc):
        self.uncaught.append((instance_id, exc))

    def update_exit_status_table(self):
        self.updated += 1


def make_dummy_self(
    *,
    num_workers=1,
    n_completed=0,
    raise_exceptions=False,
    random_delay_multiplier=0.0,
    should_skip_return=False,
    run_instance_side_effect=None,
):
    """
    Create a dummy 'self' object with the attributes/methods used by RunBatch.run_instance.
    - should_skip_return: value to return from should_skip when called (False or string)
    - run_instance_side_effect: if Exception/BaseException instance, will be raised by _run_instance;
      if callable, will be called and its return used; if None, returns default success object
    """
    d = SimpleNamespace()
    d.logger = DummyLogger()
    d._num_workers = num_workers
    d._random_delay_multiplier = random_delay_multiplier
    d._raise_exceptions = raise_exceptions

    # progress manager
    pm = DummyProgressManager(n_completed=n_completed)
    d._progress_manager = pm

    # track add/remove handler calls
    d.added_handlers = []
    d.removed_handlers = []

    def add_handlers(instance_id, multi_worker=False):
        d.added_handlers.append((instance_id, multi_worker))

    def remove_handlers(instance_id):
        d.removed_handlers.append(instance_id)

    d._add_instance_log_file_handlers = add_handlers
    d._remove_instance_log_file_handlers = remove_handlers

    # should_skip behavior
    def should_skip(instance):
        return should_skip_return

    d.should_skip = should_skip

    # _run_instance behavior
    def _run_instance(instance):
        # Raise if provided an exception or BaseException (KeyboardInterrupt is BaseException)
        if isinstance(run_instance_side_effect, BaseException):
            raise run_instance_side_effect
        if callable(run_instance_side_effect):
            return run_instance_side_effect(instance)
        # if None, return a fake successful AgentRunResult-like object
        return SimpleNamespace(info={"exit_status": "ok"})

    d._run_instance = _run_instance

    return d


def make_instance(instance_id="inst1"):
    return SimpleNamespace(problem_statement=SimpleNamespace(id=instance_id))


def bind_run_instance(dummy_self):
    # Bind the unbound function to our dummy self for testing
    return types.MethodType(run_batch.RunBatch.run_instance, dummy_self)


def test_run_instance_skips_calls_end_and_removes_handlers():
    dummy = make_dummy_self(
        num_workers=2,
        n_completed=0,
        should_skip_return="already_done",
        random_delay_multiplier=0.0,
    )
    instance = make_instance("inst-skip")
    run_fn = bind_run_instance(dummy)

    # Call and ensure it returns None and performed expected side-effects
    result = run_fn(instance)
    assert result is None

    # progress manager should have recorded start and end with skipped status
    assert dummy._progress_manager.started == ["inst-skip"]
    assert ("inst-skip", "skipped (already_done)") in dummy._progress_manager.ended

    # handlers should have been added and removed
    assert ("inst-skip", True) in dummy.added_handlers or ("inst-skip", False) in dummy.added_handlers
    assert "inst-skip" in dummy.removed_handlers

    # For the skip early-return path, the final update_exit_status_table is not called
    assert dummy._progress_manager.updated == 0


def test_run_instance_keyboardinterrupt_raises_breakloop_and_always_cleans_up():
    dummy = make_dummy_self(
        num_workers=1,
        n_completed=0,
        should_skip_return=False,
        run_instance_side_effect=KeyboardInterrupt(),
        random_delay_multiplier=0.0,
    )
    instance = make_instance("inst-ki")
    run_fn = bind_run_instance(dummy)

    with pytest.raises(run_batch._BreakLoop):
        run_fn(instance)

    # handlers removed and exit status table updated even when raising
    assert "inst-ki" in dummy.removed_handlers
    assert dummy._progress_manager.updated == 1


def test_run_instance_model_config_error_respects_raise_flag_and_logs_when_not_raising():
    # Case 1: raise_exceptions = True -> original exception propagates
    dummy_raise = make_dummy_self(
        num_workers=1,
        should_skip_return=False,
        run_instance_side_effect=ModelConfigurationError("bad config"),
        raise_exceptions=True,
        random_delay_multiplier=0.0,
    )
    instance = make_instance("inst-mce-raise")
    run_fn_raise = bind_run_instance(dummy_raise)

    with pytest.raises(ModelConfigurationError):
        run_fn_raise(instance)

    assert "inst-mce-raise" in dummy_raise.removed_handlers
    assert dummy_raise._progress_manager.updated == 1

    # Case 2: raise_exceptions = False -> should log critical and raise _BreakLoop
    dummy_no_raise = make_dummy_self(
        num_workers=1,
        should_skip_return=False,
        run_instance_side_effect=ModelConfigurationError("bad config"),
        raise_exceptions=False,
        random_delay_multiplier=0.0,
    )
    instance2 = make_instance("inst-mce-noraise")
    run_fn_no_raise = bind_run_instance(dummy_no_raise)

    with pytest.raises(run_batch._BreakLoop):
        run_fn_no_raise(instance2)

    # Check that critical log was produced
    assert len(dummy_no_raise.logger.criticals) >= 1
    # cleanup happened
    assert "inst-mce-noraise" in dummy_no_raise.removed_handlers
    assert dummy_no_raise._progress_manager.updated == 1


def test_run_instance_uncaught_exception_swallowed_or_raised_based_on_flag():
    # Swallowed case (raise_exceptions=False)
    exc = ValueError("boom")
    dummy_swallow = make_dummy_self(
        num_workers=1,
        should_skip_return=False,
        run_instance_side_effect=exc,
        raise_exceptions=False,
        random_delay_multiplier=0.0,
    )
    instance = make_instance("inst-uncaught-swallow")
    run_fn_swallow = bind_run_instance(dummy_swallow)

    # Should not raise
    run_fn_swallow(instance)

    # on_uncaught_exception should have been called with the original exception
    assert len(dummy_swallow._progress_manager.uncaught) == 1
    recorded_id, recorded_exc = dummy_swallow._progress_manager.uncaught[0]
    assert recorded_id == "inst-uncaught-swallow"
    assert isinstance(recorded_exc, ValueError)
    assert "inst-uncaught-swallow" in dummy_swallow.removed_handlers
    assert dummy_swallow._progress_manager.updated == 1

    # Raised case (raise_exceptions=True)
    dummy_raise = make_dummy_self(
        num_workers=1,
        should_skip_return=False,
        run_instance_side_effect=ValueError("boom"),
        raise_exceptions=True,
        random_delay_multiplier=0.0,
    )
    instance2 = make_instance("inst-uncaught-raise")
    run_fn_raise = bind_run_instance(dummy_raise)

    with pytest.raises(ValueError):
        run_fn_raise(instance2)

    # cleanup must still have happened
    assert "inst-uncaught-raise" in dummy_raise.removed_handlers
    assert dummy_raise._progress_manager.updated == 1
