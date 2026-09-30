import types
import pytest

import sweagent.run.run_batch as run_batch


class _DummyLiveCtx:
    def __init__(self, entered_list):
        self._entered_list = entered_list

    def __enter__(self):
        # record that the context was entered
        self._entered_list.append(True)
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyLiveFactory:
    def __init__(self, entered_list):
        self._entered_list = entered_list

    def __call__(self, *args, **kwargs):
        return _DummyLiveCtx(self._entered_list)


def _make_minimal_runbatch():
    # Create instance without invoking __init__ to avoid side effects
    rb = object.__new__(run_batch.RunBatch)
    return rb


def test_live_entered_round_087(monkeypatch):
    rb = _make_minimal_runbatch()

    # Monkeypatch the class _model_id property to be 'gpt-xyz' (read-only)
    monkeypatch.setattr(run_batch.RunBatch, "_model_id", property(lambda self: "gpt-xyz"))

    # Prepare other attributes expected by main_single_worker
    rb._show_progress_bar = True

    # progress_manager.render_group can be any object
    class PM:
        render_group = object()

    rb._progress_manager = PM()

    # Instances: simulate two items
    processed = []
    rb.instances = ["a", "b"]

    def run_instance(instance):
        processed.append(instance)

    rb.run_instance = run_instance

    # Provide a dummy logger with an info method (not expected to be used here)
    rb.logger = types.SimpleNamespace(info=lambda *a, **k: None)

    # Patch Live in the module to a dummy that records enters
    live_entered = []
    monkeypatch.setattr(run_batch, "Live", _DummyLiveFactory(live_entered))

    # Execute
    rb.main_single_worker()

    # Assertions: Live should have been entered once, and both instances processed
    assert len(live_entered) == 1, "Live context should be entered when model is not human and progress shown"
    assert processed == ["a", "b"]


def test_breakloop_and_human_skip_round_087(monkeypatch):
    rb = _make_minimal_runbatch()

    # Monkeypatch the class _model_id property to be 'human'
    monkeypatch.setattr(run_batch.RunBatch, "_model_id", property(lambda self: "human"))

    rb._show_progress_bar = True

    class PM:
        render_group = object()

    rb._progress_manager = PM()

    # Instances: two items but run_instance will raise _BreakLoop on first
    rb.instances = [1, 2]

    call_count = {"n": 0}

    def run_instance(instance):
        call_count["n"] += 1
        # Raise the module's _BreakLoop to trigger the except branch
        raise run_batch._BreakLoop()

    rb.run_instance = run_instance

    # Capture logger.info calls
    info_calls = []

    def fake_info(msg, *a, **k):
        info_calls.append(msg)

    rb.logger = types.SimpleNamespace(info=fake_info)

    # Patch Live to detect if called; should NOT be called for human model
    live_entered = []
    monkeypatch.setattr(run_batch, "Live", _DummyLiveFactory(live_entered))

    # Execute
    rb.main_single_worker()

    # After the BreakLoop, loop must stop: run_instance should have been called once
    assert call_count["n"] == 1, "run_instance should be called once before BreakLoop stops the loop"

    # Logger should have been informed of stopping
    assert info_calls == ["Stopping loop over instances"]

    # Live should not have been entered for human model
    assert live_entered == [], "Live should not be entered when model_id is 'human' even if _show_progress_bar is True"
