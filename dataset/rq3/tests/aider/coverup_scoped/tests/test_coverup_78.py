# file: aider/gui.py:52-61
# asked: {"lines": [52, 53, 55, 56, 57, 59, 60, 61], "branches": [[56, 57], [56, 59]]}
# gained: {"lines": [52, 53, 55, 56, 57, 59, 60, 61], "branches": [[56, 57], [56, 59]]}

import pytest
from aider.gui import State

def test_init_adds_key_and_sets_attribute_and_returns_true():
    # Save original class-level keys to restore later
    original_keys = set(State.keys)
    try:
        # Ensure starting from a clean state
        State.keys.clear()

        s = State()
        # Call init for a key not present yet - should add and return True
        res = s.init("test_key", 123)
        assert res is True
        # The key should be in the class-level keys set
        assert "test_key" in State.keys
        # The instance should have the attribute set to the provided value
        assert getattr(s, "test_key") == 123

        # Calling init again with the same key should return None and not overwrite attribute
        res2 = s.init("test_key", 456)
        assert res2 is None
        assert getattr(s, "test_key") == 123

    finally:
        # Clean up: remove attribute from instance if present and restore class keys
        try:
            delattr(s, "test_key")
        except Exception:
            pass
        State.keys.clear()
        State.keys.update(original_keys)


def test_init_returns_none_when_key_already_in_class_keys_and_does_not_set_attribute():
    original_keys = set(State.keys)
    try:
        State.keys.clear()
        # Pre-populate the class-level keys to simulate that the key is already initialized
        State.keys.add("existing_key")

        s2 = State()
        # Since "existing_key" is already present in State.keys, init should return None
        res = s2.init("existing_key", "value")
        assert res is None
        # The instance should NOT have the attribute set because init returned early
        assert not hasattr(s2, "existing_key")

    finally:
        # Restore original keys
        State.keys.clear()
        State.keys.update(original_keys)
