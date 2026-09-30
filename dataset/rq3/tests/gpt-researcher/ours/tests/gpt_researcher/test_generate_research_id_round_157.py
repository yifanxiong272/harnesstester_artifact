import sys
import types
from gpt_researcher import agent


def _make_fake_modules(hex_digest: str, timestamp: float):
    """Create fake hashlib and time modules for deterministic id generation."""
    fake_time = types.ModuleType("time")
    fake_time.time = lambda: timestamp

    fake_hashlib = types.ModuleType("hashlib")

    def md5(data):
        class H:
            def __init__(self, data):
                self.data = data

            def hexdigest(self):
                return hex_digest

        return H(data)

    fake_hashlib.md5 = md5
    return fake_hashlib, fake_time


class DummySelf:
    pass


def test_generate_new_research_id_round_157():
    """When _research_id is falsy, a deterministic id is created using time and hashlib."""
    # Prepare deterministic fake modules
    hex_digest = "0123456789abcdef"
    timestamp = 12345.6789
    fake_hashlib, fake_time = _make_fake_modules(hex_digest, timestamp)

    # Save originals to restore later
    orig_hashlib = sys.modules.get("hashlib")
    orig_time = sys.modules.get("time")

    try:
        # Insert fakes so the in-function imports pick them up
        sys.modules["hashlib"] = fake_hashlib
        sys.modules["time"] = fake_time

        dummy = DummySelf()
        dummy.query = "myquery"
        # _research_id falsy -> branch that generates a new id
        dummy._research_id = ""

        # Call the unbound function on our dummy instance
        result = agent.GPTResearcher._generate_research_id(dummy)

        # Expected pattern: research_<first 12 chars of hexdigest>
        expected = "research_" + hex_digest[:12]
        assert result == expected
        # Also ensure the attribute was set on the instance
        assert getattr(dummy, "_research_id") == expected
    finally:
        # Restore original modules to avoid side effects
        if orig_hashlib is None:
            sys.modules.pop("hashlib", None)
        else:
            sys.modules["hashlib"] = orig_hashlib

        if orig_time is None:
            sys.modules.pop("time", None)
        else:
            sys.modules["time"] = orig_time


def test_return_existing_research_id_round_157():
    """When _research_id is already truthy, the method returns it unchanged (skips generation branch)."""
    dummy = DummySelf()
    dummy.query = "another"
    dummy._research_id = "existing_research_id"

    # Ensure we return the existing id and it remains unchanged
    result = agent.GPTResearcher._generate_research_id(dummy)
    assert result == "existing_research_id"
    assert dummy._research_id == "existing_research_id"
