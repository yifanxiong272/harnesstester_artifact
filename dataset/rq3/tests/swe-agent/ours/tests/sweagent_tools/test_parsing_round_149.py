import pytest

from sweagent.tools.parsing import AbstractParseFunction


def test_abstract_call_raises_not_implemented_round_149():
    """Directly call the unbound AbstractParseFunction.__call__ to exercise the
    NotImplementedError at line 62 without instantiating the ABC.
    """
    # Call the function as an unbound function, providing a dummy self.
    dummy_self = object()
    with pytest.raises(NotImplementedError):
        AbstractParseFunction.__call__(dummy_self, model_response="x", commands=[], strict=False)
