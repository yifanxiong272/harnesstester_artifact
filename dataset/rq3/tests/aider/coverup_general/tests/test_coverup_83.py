# file: aider/coders/chat_chunks.py:43-55
# asked: {"lines": [44, 45, 47, 48, 49, 50, 51, 53, 55], "branches": [[44, 45], [44, 47], [48, 49], [48, 53]]}
# gained: {"lines": [44, 45, 47, 48, 49, 50, 51, 53, 55], "branches": [[44, 45], [44, 47], [48, 49], [48, 53]]}

import pytest
from copy import deepcopy
from aider.coders.chat_chunks import ChatChunks


def test_add_cache_control_no_messages():
    cc = ChatChunks()
    messages = []
    # Should return None and not raise
    result = cc.add_cache_control(messages)
    assert result is None
    # messages should remain unchanged
    assert messages == []


def test_add_cache_control_with_str_content():
    cc = ChatChunks()
    messages = [{"role": "assistant", "content": "Hello world"}]
    # Keep a copy to ensure no other elements are modified
    before = deepcopy(messages)
    cc.add_cache_control(messages)

    # After calling, last message's content must be a list with one dict
    assert isinstance(messages[-1]["content"], list)
    assert len(messages[-1]["content"]) == 1

    content = messages[-1]["content"][0]
    # The function should have converted the string into a dict with type and text
    assert content["type"] == "text"
    assert content["text"] == before[-1]["content"]
    # And added cache_control key with ephemeral type
    assert "cache_control" in content
    assert content["cache_control"] == {"type": "ephemeral"}


def test_add_cache_control_with_dict_content():
    cc = ChatChunks()
    original_content = {"type": "code", "text": "print('x')"}
    messages = [{"role": "assistant", "content": original_content}]
    cc.add_cache_control(messages)

    # After calling, last message's content must be a list with one dict
    assert isinstance(messages[-1]["content"], list)
    assert len(messages[-1]["content"]) == 1

    content = messages[-1]["content"][0]
    # The original dict should be preserved (but now with cache_control)
    assert content["type"] == original_content["type"]
    assert content["text"] == original_content["text"]
    assert "cache_control" in content
    assert content["cache_control"] == {"type": "ephemeral"}
