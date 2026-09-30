# file: sweagent/agent/history_processors.py:45-59
# asked: {"lines": [58, 59], "branches": [[56, 58]]}
# gained: {"lines": [58, 59], "branches": [[56, 58]]}

import copy
import pytest

from sweagent.agent.history_processors import _set_cache_control


def test_set_cache_control_converts_nonlist_and_sets_inner_cache_control():
    entry = {"role": "assistant", "content": "hello world"}
    original = copy.deepcopy(entry)
    _set_cache_control(entry)

    # content should be converted to a list with a single text item
    assert isinstance(entry["content"], list), "content was not converted to a list"
    assert len(entry["content"]) == 1
    item = entry["content"][0]
    assert item["type"] == "text"
    assert item["text"] == original["content"]
    # inner cache_control should be set for non-tool roles
    assert item["cache_control"] == {"type": "ephemeral"}
    # top-level cache_control should not be set for non-tool roles
    assert "cache_control" not in entry


def test_set_cache_control_for_tool_moves_cache_control_from_inner_to_top_level_with_list():
    entry = {"role": "tool", "content": [{"type": "text", "text": "result from tool"}]}
    _set_cache_control(entry)

    # content remains a list
    assert isinstance(entry["content"], list)
    assert len(entry["content"]) == 1
    # inner cache_control must have been removed by the tool-workaround
    assert "cache_control" not in entry["content"][0]
    # top-level cache_control must be set
    assert entry.get("cache_control") == {"type": "ephemeral"}


def test_set_cache_control_for_tool_moves_cache_control_from_inner_to_top_level_with_nonlist():
    entry = {"role": "tool", "content": "raw tool output"}
    _set_cache_control(entry)

    # content converted to list
    assert isinstance(entry["content"], list)
    assert len(entry["content"]) == 1
    # inner cache control removed by workaround for tool role
    assert "cache_control" not in entry["content"][0]
    # top-level cache_control set
    assert entry.get("cache_control") == {"type": "ephemeral"}
