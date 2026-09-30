import pytest

from aider.coders.chat_chunks import ChatChunks


def test_add_cache_control_empty_round_153():
    """When messages is empty, the method should return early and not raise."""
    messages = []

    # Call the unbound function with a dummy self (the implementation does not use self)
    result = ChatChunks.add_cache_control(None, messages)

    # Should return None and leave the list untouched
    assert result is None
    assert messages == []


def test_add_cache_control_with_str_content_round_153():
    """When the last message content is a string, it should be converted to a dict,
    receive a cache_control entry, and be wrapped in a list.
    """
    messages = [{"role": "assistant", "content": "hello world"}]

    ChatChunks.add_cache_control(None, messages)

    # After the call, the last message's content must be a single-element list
    assert isinstance(messages[-1]["content"], list)
    assert len(messages[-1]["content"]) == 1

    content_obj = messages[-1]["content"][0]

    # The function constructs the dict with these exact keys for string input
    assert content_obj["type"] == "text"
    assert content_obj["text"] == "hello world"

    # And it must add the expected cache_control entry
    assert content_obj["cache_control"] == {"type": "ephemeral"}


def test_add_cache_control_with_dict_content_preserves_and_mutates_round_153():
    """When the last message content is already a dict, the function should
    mutate that dict by adding cache_control and then wrap it in a list.
    """
    original_content = {"type": "code", "text": "print(1)"}
    messages = [{"role": "assistant", "content": original_content}]

    # Keep identity to ensure the same dict object is used after the call
    orig_id = id(original_content)

    ChatChunks.add_cache_control(None, messages)

    # messages[-1]["content"] must now be a list with the same dict object inside
    assert isinstance(messages[-1]["content"], list)
    assert len(messages[-1]["content"]) == 1
    wrapped = messages[-1]["content"][0]

    # Identity preserved
    assert id(wrapped) == orig_id

    # Original fields remain and cache_control was added
    assert wrapped["type"] == "code"
    assert wrapped["text"] == "print(1)"
    assert wrapped["cache_control"] == {"type": "ephemeral"}
