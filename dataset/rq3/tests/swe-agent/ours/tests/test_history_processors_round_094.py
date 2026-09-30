import pytest

from sweagent.agent.history_processors import _set_cache_control


def test_set_cache_control_tool_with_string_content_round_094():
    # content is a non-list (string) -> should be converted into list with a text item
    entry = {"role": "tool", "content": "hello world"}

    _set_cache_control(entry)

    # Top-level cache_control must be set for tools
    assert entry.get("cache_control") == {"type": "ephemeral"}

    # The content should have been normalized to a list with a dict item
    assert isinstance(entry["content"], list)
    first = entry["content"][0]
    assert first["type"] == "text"
    assert first["text"] == "hello world"

    # Workaround should have removed the nested cache_control from the content[0]
    assert "cache_control" not in first


def test_set_cache_control_tool_with_list_content_round_094():
    # content is already a list and contains an existing cache_control -> replaced then popped
    entry = {
        "role": "tool",
        "content": [
            {
                "type": "text",
                "text": "preserve this text",
                "cache_control": {"type": "permanent"},
            }
        ],
    }

    _set_cache_control(entry)

    # Top-level cache_control must be set for tools
    assert entry.get("cache_control") == {"type": "ephemeral"}

    # The original text must be preserved
    assert entry["content"][0]["text"] == "preserve this text"

    # The nested cache_control must have been removed by the workaround
    assert "cache_control" not in entry["content"][0]
