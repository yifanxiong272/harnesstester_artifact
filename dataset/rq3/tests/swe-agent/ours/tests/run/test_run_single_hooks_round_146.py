import pytest

from sweagent.run.run_single import RunSingle


def test_hooks_returns_underlying_hooks_round_146():
    """Ensure RunSingle.hooks returns the underlying _chooks.hooks list and reflects mutations."""
    # Bypass __init__ to set up a minimal instance with a synthetic _chooks
    rs = object.__new__(RunSingle)

    class DummyCombined:
        def __init__(self):
            self.hooks = ["hook1", "hook2"]

    dummy = DummyCombined()
    rs._chooks = dummy

    # The property should return the exact underlying list object
    returned = rs.hooks
    assert returned is dummy.hooks
    assert returned == ["hook1", "hook2"]

    # Mutating the underlying list should be visible through the property
    dummy.hooks.append("hook3")
    assert rs.hooks[-1] == "hook3"


def test_hooks_missing_attribute_raises_round_146():
    """Ensure access raises AttributeError if _chooks lacks a hooks attribute."""
    rs = object.__new__(RunSingle)

    # _chooks object without a 'hooks' attribute
    class BrokenCombined:
        pass

    rs._chooks = BrokenCombined()

    with pytest.raises(AttributeError):
        _ = rs.hooks
