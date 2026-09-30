# file: sweagent/agent/history_processors.py:30-35
# asked: {"lines": [34, 35], "branches": [[31, 34]]}
# gained: {"lines": [34, 35], "branches": [[31, 34]]}

import pytest
from sweagent.agent.history_processors import _set_content_text


def test_set_content_text_with_single_message_list():
    # content is a list with a single message dict -> should update that dict's 'text'
    entry = {"content": [{"text": "original"}]}
    _set_content_text(entry, "updated")
    assert isinstance(entry["content"], list)
    assert len(entry["content"]) == 1
    assert entry["content"][0]["text"] == "updated"


def test_set_content_text_with_multiple_messages_raises_assertion():
    # content is a list with multiple messages -> should raise the assertion from the function
    entry = {"content": [{"text": "one"}, {"text": "two"}]}
    with pytest.raises(AssertionError) as excinfo:
        _set_content_text(entry, "won't matter")
    # Ensure the assertion message matches the one in the source
    assert "Expected single message in content" in str(excinfo.value)
    # ensure the entry was not mutated
    assert entry["content"][0]["text"] == "one"
    assert entry["content"][1]["text"] == "two"


def test_set_content_text_with_string_replaces_content():
    # content is a string -> should replace the content value with the provided text
    entry = {"content": "some text"}
    _set_content_text(entry, "new text")
    assert isinstance(entry["content"], str)
    assert entry["content"] == "new text"
