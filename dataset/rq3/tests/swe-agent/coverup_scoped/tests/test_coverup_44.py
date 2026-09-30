# file: sweagent/tools/tools.py:334-348
# asked: {"lines": [338, 345, 347], "branches": [[337, 338], [344, 347]]}
# gained: {"lines": [338, 345, 347], "branches": [[337, 338], [344, 347]]}

import re
from types import SimpleNamespace

import pytest

from sweagent.tools.tools import ToolHandler


class FakeFilter:
    def __init__(self, blocklist=None, blocklist_standalone=None, block_unless_regex=None):
        self.blocklist = blocklist if blocklist is not None else []
        self.blocklist_standalone = blocklist_standalone if blocklist_standalone is not None else []
        self.block_unless_regex = block_unless_regex if block_unless_regex is not None else {}


class FakeTools:
    def __init__(self, fake_filter: FakeFilter):
        self._fake_filter = fake_filter

    def model_copy(self, deep: bool = False):
        # Return an object that has a 'filter' attribute like the real config
        return SimpleNamespace(filter=self._fake_filter)


def make_handler_with_filter(fake_filter: FakeFilter, monkeypatch) -> ToolHandler:
    # Ensure _get_command_patterns doesn't depend on real config during init
    monkeypatch.setattr(ToolHandler, "_get_command_patterns", lambda self: {})
    return ToolHandler(FakeTools(fake_filter))


def test_should_block_action_empty_string(monkeypatch):
    # Arrange: filter with nothing that would block
    fake_filter = FakeFilter(blocklist=[], blocklist_standalone=[], block_unless_regex={})
    handler = make_handler_with_filter(fake_filter, monkeypatch)

    # Act: pass an action that's only whitespace (should be trimmed to empty)
    result = handler.should_block_action("   \n\t  ")

    # Assert: empty action should not be blocked (covers the early return)
    assert result is False


def test_should_block_action_block_unless_regex_blocks_and_allows(monkeypatch):
    # Arrange:
    # - For name 'echo' provide a regex that does NOT match the action -> should block (True)
    # - Then change regex to one that matches -> should NOT block (False)
    fake_filter = FakeFilter(
        blocklist=[],
        blocklist_standalone=[],
        block_unless_regex={"echo": r"^ls\s"}  # does not match "echo hello"
    )
    handler = make_handler_with_filter(fake_filter, monkeypatch)

    # Act & Assert: regex does not match, so should_block_action returns True (covers lines 344-347)
    assert handler.should_block_action("echo hello") is True

    # Now update the regex so it matches the action and verify it is not blocked
    handler.config.filter.block_unless_regex["echo"] = r"^echo\b"
    assert handler.should_block_action("echo hello") is False

    # Also verify that unrelated names are not affected
    assert handler.should_block_action("othercmd arg") is False
