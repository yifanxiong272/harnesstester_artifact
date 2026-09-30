import pytest


def _make_instance():
    # Import the module under test if available; otherwise skip these tests.
    mod = pytest.importorskip("sweagent.environment.swe_env")
    SWEEnv = getattr(mod, "SWEEnv")
    # Create an instance without calling __init__ to avoid heavy construction.
    inst = object.__new__(SWEEnv)
    return inst


def test_hard_reset_calls_close_then_start_round_124():
    """Ensure hard_reset calls close() then start() in that order."""
    inst = _make_instance()
    calls = []

    # Attach simple callables to record invocation order.
    inst.close = lambda: calls.append("close")
    inst.start = lambda: calls.append("start")

    # Invoke the method under test
    inst.hard_reset()

    # Oracle: close must be called before start, exact order
    assert calls == ["close", "start"]


def test_hard_reset_propagates_close_exception_round_124():
    """If close() raises, hard_reset should propagate and start() must not be called."""
    inst = _make_instance()
    calls = []

    def raising_close():
        raise RuntimeError("close-failed")

    inst.close = raising_close
    inst.start = lambda: calls.append("start")

    with pytest.raises(RuntimeError, match="close-failed"):
        inst.hard_reset()

    # Oracle: start must not have been invoked when close raised
    assert calls == []
