import pytest

# Import the class under test. The module defines ToolHandler.from_config as a simple
# classmethod that returns cls(config). We avoid triggering heavy initialization
# in the real ToolHandler by creating a lightweight subclass that captures the
# argument passed to __init__.
from sweagent.tools.tools import ToolHandler


class CapturingToolHandler(ToolHandler):
    """A minimal subclass that records the constructor argument without
    invoking any parent initialization logic."""

    def __init__(self, config):
        # Intentionally do not call super().__init__ to avoid side effects.
        self._captured_config = config


def test_from_config_passes_config_round_152():
    cfg = {"name": "dummy", "value": 123}
    inst = CapturingToolHandler.from_config(cfg)

    # Oracle: from_config should construct cls(config), so the returned
    # instance must be the subclass and must have received the exact object.
    assert isinstance(inst, CapturingToolHandler)
    # Use 'is' to ensure the exact object passed through (deterministic).
    assert inst._captured_config is cfg


def test_from_config_passes_none_round_152():
    # Also assert behavior when None is passed through.
    inst = CapturingToolHandler.from_config(None)
    assert isinstance(inst, CapturingToolHandler)
    assert inst._captured_config is None
