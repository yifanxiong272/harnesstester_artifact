import pytest

from aider.gui import State


def test_init_adds_key_and_sets_attribute_round_171():
    # Ensure a fresh class-level keys set so tests are deterministic
    State.keys = set()

    s = State()
    # Precondition: key should not be present
    assert "foo" not in State.keys

    # Call init for a new key -> should add the key, set the attribute on the instance, and return True
    result = s.init("foo", 123)
    assert result is True
    assert "foo" in State.keys
    assert getattr(s, "foo") == 123

    # A new instance should not automatically have the attribute (it's set on the instance that called init)
    s2 = State()
    assert not hasattr(s2, "foo")


def test_init_noop_if_key_exists_round_171():
    # Start from a known class-level keys state containing 'bar'
    State.keys = {"bar"}

    s = State()
    # Precondition: key is already recorded in the shared keys set
    assert "bar" in State.keys
    # And the instance does not yet have the attribute
    assert not hasattr(s, "bar")

    # Calling init for an existing key should return None and must not set the attribute on the instance
    result = s.init("bar", 999)
    assert result is None
    assert not hasattr(s, "bar")

    # The shared keys set should remain unchanged
    assert State.keys == {"bar"}
