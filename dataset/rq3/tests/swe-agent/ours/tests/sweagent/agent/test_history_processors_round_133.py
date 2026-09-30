import pytest
from sweagent.agent.history_processors import AbstractHistoryProcessor


def test_abstract_processor_call_raises_NotImplementedError_round_133():
    """Ensure the protocol's __call__ raises the NotImplementedError defined on the base implementation.

    Some typing.Protocol subclasses may not be instantiable in all environments. To deterministically
    exercise the base implementation (and hit the raise on line 16), this test will attempt to
    instantiate the protocol; if instantiation is blocked, it will call the function unbound with a
    dummy self. Either way, the call should raise NotImplementedError.
    """
    try:
        instance = AbstractHistoryProcessor()
    except TypeError:
        # If the Protocol is not instantiable, call the underlying function with a dummy self.
        instance = object()

    with pytest.raises(NotImplementedError):
        # Call the class-defined implementation directly to ensure we exercise the raise statement.
        AbstractHistoryProcessor.__call__(instance, {})


def test_concrete_subclass_overrides_call_round_133():
    """A concrete subclass should be able to override __call__ and return a history without raising.

    This verifies that the base class's NotImplementedError is only raised when no override is provided.
    """
    class ConcreteProcessor(AbstractHistoryProcessor):
        def __call__(self, history):
            # Return a shallow-modified history to make the output observable and deterministic.
            try:
                # If history is a list-like, produce a new list
                return list(history) + ["processed"]
            except TypeError:
                # Otherwise, return a predictable tuple
                return (history, "processed")

    proc = ConcreteProcessor()

    # Case A: list-like history
    hist_in = [1, 2]
    hist_out = proc(hist_in)
    assert hist_out == [1, 2, "processed"]

    # Case B: non-list history (e.g., dict) -> will return a tuple as fallback
    hist_in2 = {"k": "v"}
    hist_out2 = proc(hist_in2)
    assert hist_out2 == (hist_in2, "processed")
