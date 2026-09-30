import types
import pytest

import sweagent.run.run_batch as run_batch


def _call_evaluate_and_redo_existing_on(obj):
    """Call the original evaluate_and_redo_existing implementation on a stand-in object.

    Prefer the underlying wrapped function if available; otherwise bind the descriptor.
    """
    validator = getattr(
        run_batch.RunBatchConfig.evaluate_and_redo_existing, "__wrapped__", None
    )
    if validator is not None:
        return validator(obj)

    attr = run_batch.RunBatchConfig.evaluate_and_redo_existing
    try:
        bound = attr.__get__(obj, run_batch.RunBatchConfig)
        return bound()
    except Exception:
        return attr(obj)


def test_not_sweb_instances_round_064():
    """If instances is not a SWEBenchInstances instance, the validator returns self."""
    standin = types.SimpleNamespace()
    # Use a plain object that is definitely not an instance of SWEBenchInstances
    standin.instances = object()
    standin.redo_existing = True

    result = _call_evaluate_and_redo_existing_on(standin)

    # The method should return the same object (self) unchanged
    assert result is standin


def test_evaluate_and_redo_conflict_raises_round_064(monkeypatch):
    """When instances is SWEBenchInstances with evaluate=True and redo_existing=True,
    the validator must raise a ValueError with the explanatory message.

    Monkeypatch SWEBenchInstances to a simple class so we can create instances without
    invoking Pydantic internals.
    """
    DummySWEB = type("DummySWEB", (), {})
    monkeypatch.setattr(run_batch, "SWEBenchInstances", DummySWEB)

    sweb = DummySWEB()
    setattr(sweb, "evaluate", True)

    standin = types.SimpleNamespace()
    standin.instances = sweb
    standin.redo_existing = True

    with pytest.raises(ValueError) as excinfo:
        _call_evaluate_and_redo_existing_on(standin)

    # Check the message explains the conflict to ensure the correct branch was taken
    assert "Cannot evaluate and redo existing" in str(excinfo.value)


def test_sweb_instances_without_conflict_round_064(monkeypatch):
    """When instances is SWEBenchInstances but evaluate is False (or redo_existing False),
    the validator should not raise and should return self.
    """
    DummySWEB = type("DummySWEB", (), {})
    monkeypatch.setattr(run_batch, "SWEBenchInstances", DummySWEB)

    sweb = DummySWEB()
    setattr(sweb, "evaluate", False)

    standin = types.SimpleNamespace()
    standin.instances = sweb
    standin.redo_existing = True

    result = _call_evaluate_and_redo_existing_on(standin)
    assert result is standin

    # Also test the symmetrical case: evaluate True but redo_existing False
    setattr(sweb, "evaluate", True)
    standin2 = types.SimpleNamespace()
    standin2.instances = sweb
    standin2.redo_existing = False

    result2 = _call_evaluate_and_redo_existing_on(standin2)
    assert result2 is standin2
