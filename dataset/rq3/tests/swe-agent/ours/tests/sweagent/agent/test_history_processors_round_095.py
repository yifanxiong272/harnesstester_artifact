import pytest

from sweagent.agent.history_processors import LastNObservations


def _call_validate_n(n):
    """Call the class-level validator in a way that is robust to descriptor wrapping

    The field_validator decorator used by pydantic can wrap the original function
    such that accessing it on the class may present a callable that expects a
    different binding pattern. Try the common calling convention first (fn(n)),
    and on TypeError fall back to invoking the raw attribute from the class
    dictionary with (cls, n).
    """
    fn = getattr(LastNObservations, "validate_n")
    try:
        # Common case: validator is callable as fn(n)
        return fn(n)
    except TypeError:
        # Fallback: call the raw function object with the class as first arg
        raw = LastNObservations.__dict__["validate_n"]
        return raw(LastNObservations, n)


def test_validate_n_positive_round_095():
    """When n is a positive integer, validate_n should return it unchanged."""
    result = _call_validate_n(3)
    assert isinstance(result, int)
    assert result == 3


def test_validate_n_zero_raises_round_095():
    """When n is zero (not positive), validate_n should raise ValueError with the exact message."""
    with pytest.raises(ValueError) as excinfo:
        _call_validate_n(0)
    assert str(excinfo.value) == "n must be a positive integer"
