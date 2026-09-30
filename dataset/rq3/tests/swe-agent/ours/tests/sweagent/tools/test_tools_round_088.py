import re
from types import SimpleNamespace
import pytest

from sweagent.tools.tools import ToolHandler


def _make_handler_with_filter(filter_obj):
    """Create a ToolHandler with a fake tools/config provider.

    ToolHandler.__init__ expects its 'tools' argument to implement model_copy(deep=True).
    We also patch ToolHandler._get_command_patterns during construction to avoid
    requiring other config attributes used by that helper.
    """
    class FakeTools:
        def __init__(self, filter_obj):
            self._filter = filter_obj

        def model_copy(self, deep=True):
            # Return an object that provides the expected 'filter' attribute
            return SimpleNamespace(filter=self._filter)

    # Patch _get_command_patterns to a noop to prevent reliance on other config fields
    orig_get_patterns = ToolHandler._get_command_patterns
    ToolHandler._get_command_patterns = lambda self: []
    try:
        handler = ToolHandler(FakeTools(filter_obj))
    finally:
        # restore to avoid affecting other tests
        ToolHandler._get_command_patterns = orig_get_patterns
    return handler


def test_empty_action_round_088():
    """An action consisting only of whitespace should be treated as empty
    after strip() and should not be blocked (returns False).
    """
    filt = SimpleNamespace(blocklist=[], blocklist_standalone=set(), block_unless_regex={})
    handler = _make_handler_with_filter(filt)

    # action containing only spaces should be stripped to empty -> early False
    assert handler.should_block_action("   ") is False


def test_block_unless_regex_no_match_round_088():
    """If the action name appears in block_unless_regex and the regex does
    NOT match the action, the action must be blocked (returns True).
    """
    filt = SimpleNamespace(
        blocklist=[],
        blocklist_standalone=set(),
        block_unless_regex={"danger": r"^safe$"},
    )
    handler = _make_handler_with_filter(filt)

    action = "danger do something unsafe"
    # regex '^safe$' will not match 'danger do something unsafe' -> should be blocked
    assert handler.should_block_action(action) is True


def test_block_unless_regex_match_no_block_round_088():
    """If the action name appears in block_unless_regex and the regex DOES
    match the action, the action should NOT be blocked (returns False).
    """
    filt = SimpleNamespace(
        blocklist=[],
        blocklist_standalone=set(),
        block_unless_regex={"danger": r"safe|ok"},
    )
    handler = _make_handler_with_filter(filt)

    action = "danger safe proceed"
    # regex 'safe|ok' matches -> should not be blocked
    assert handler.should_block_action(action) is False
