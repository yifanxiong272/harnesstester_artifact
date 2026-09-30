# file: browser_use/llm/anthropic/serializer.py:172-256
# asked: {"lines": [180, 181, 182, 184, 187, 189, 191, 194, 195, 197, 198, 199, 200, 201, 202, 208, 210, 211, 212, 213, 214, 223, 224, 225, 227, 231, 232, 233, 234, 240, 241, 244, 245, 246, 248, 250, 251, 252, 256], "branches": [[180, 181], [180, 184], [184, 187], [184, 189], [189, 191], [189, 256], [194, 195], [194, 223], [195, 197], [195, 208], [208, 210], [208, 223], [211, 208], [211, 212], [223, 224], [223, 231], [231, 232], [231, 240], [240, 241], [240, 244], [245, 246], [245, 248]]}
# gained: {"lines": [180, 181, 182, 184, 187, 189, 191, 194, 195, 197, 198, 199, 200, 201, 202, 208, 210, 211, 212, 213, 214, 223, 224, 225, 227, 231, 240, 241, 244, 245, 246, 248, 250, 251, 252, 256], "branches": [[180, 181], [180, 184], [184, 187], [184, 189], [189, 191], [189, 256], [194, 195], [194, 223], [195, 197], [195, 208], [208, 210], [208, 223], [211, 212], [223, 224], [223, 231], [231, 240], [240, 241], [240, 244], [245, 246], [245, 248]]}

import pytest
from types import SimpleNamespace

import browser_use.llm.anthropic.serializer as serializer


def test_serialize_user_message_calls_serialize_content_and_builds_messageparam(monkeypatch):
    """UserMessage branch: ensure _serialize_content is called and MessageParam constructed."""
    sentinel = object()

    def fake_serialize_content(content, use_cache):
        assert content == "user text"
        assert use_cache is True
        return sentinel

    def fake_message_param(**kwargs):
        return kwargs

    # Replace message classes so isinstance checks work with our subclasses below
    monkeypatch.setattr(serializer, "UserMessage", type("UserMessageClass", (), {}))
    monkeypatch.setattr(serializer, "SystemMessage", type("SystemMessageClass", (), {}))
    monkeypatch.setattr(serializer, "AssistantMessage", type("AssistantMessageClass", (), {}))

    # Patch the class method on AnthropicMessageSerializer
    monkeypatch.setattr(
        serializer.AnthropicMessageSerializer, "_serialize_content", staticmethod(fake_serialize_content)
    )
    monkeypatch.setattr(serializer, "MessageParam", fake_message_param)

    # Create a UserMessage instance (subclass of our monkeypatched UserMessage)
    class UserMessageInstance(serializer.UserMessage):
        def __init__(self):
            self.content = "user text"
            self.cache = True

    um = UserMessageInstance()

    result = serializer.AnthropicMessageSerializer.serialize(um)

    assert isinstance(result, dict)
    assert result["role"] == "user"
    assert result["content"] is sentinel


def test_serialize_system_message_returns_same_object(monkeypatch):
    """SystemMessage branch should return the original object unchanged."""
    monkeypatch.setattr(serializer, "UserMessage", type("UserMessageClass", (), {}))
    monkeypatch.setattr(serializer, "SystemMessage", type("SystemMessageClass", (), {}))
    monkeypatch.setattr(serializer, "AssistantMessage", type("AssistantMessageClass", (), {}))

    class Sys(serializer.SystemMessage):
        pass

    s = Sys()
    returned = serializer.AnthropicMessageSerializer.serialize(s)
    assert returned is s


def test_serialize_assistant_with_string_content_and_caching_returns_blocks(monkeypatch):
    """AssistantMessage with string content and caching enabled should return blocks (list)."""
    monkeypatch.setattr(serializer, "UserMessage", type("UserMessageClass", (), {}))
    monkeypatch.setattr(serializer, "SystemMessage", type("SystemMessageClass", (), {}))
    monkeypatch.setattr(serializer, "AssistantMessage", type("AssistantMessageClass", (), {}))

    def fake_cache_control(use_cache):
        assert use_cache is True
        return {"ephemeral": True}

    def fake_text_block_param(text, type, cache_control=None):
        return {"text": text, "type": type, "cache_control": cache_control}

    def fake_message_param(**kwargs):
        return kwargs

    monkeypatch.setattr(
        serializer.AnthropicMessageSerializer, "_serialize_cache_control", staticmethod(fake_cache_control)
    )
    monkeypatch.setattr(serializer, "TextBlockParam", fake_text_block_param)
    monkeypatch.setattr(serializer, "MessageParam", fake_message_param)

    class Assist(serializer.AssistantMessage):
        def __init__(self):
            self.content = "assistant reply"
            self.cache = True
            self.tool_calls = False

    am = Assist()
    result = serializer.AnthropicMessageSerializer.serialize(am)
    assert result["role"] == "assistant"
    assert isinstance(result["content"], list)
    assert result["content"][0]["text"] == "assistant reply"
    assert result["content"][0]["type"] == "text"
    assert result["content"][0]["cache_control"] == {"ephemeral": True}


def test_serialize_assistant_with_list_content_and_no_cache_simplifies_to_string(monkeypatch):
    """AssistantMessage with content parts list and no cache and no tool calls should simplify to string."""
    monkeypatch.setattr(serializer, "UserMessage", type("UserMessageClass", (), {}))
    monkeypatch.setattr(serializer, "SystemMessage", type("SystemMessageClass", (), {}))
    monkeypatch.setattr(serializer, "AssistantMessage", type("AssistantMessageClass", (), {}))

    def fake_serialize_content_part_text(part, use_cache):
        # use_cache should be False because message.cache False and it's the only/last content
        assert use_cache is False
        return {"type": "text", "text": part.text}

    def fake_message_param(**kwargs):
        return kwargs

    monkeypatch.setattr(
        serializer.AnthropicMessageSerializer, "_serialize_content_part_text", staticmethod(fake_serialize_content_part_text)
    )
    monkeypatch.setattr(serializer, "MessageParam", fake_message_param)

    class Assist(serializer.AssistantMessage):
        def __init__(self):
            # content parts must have attributes 'type' and 'text' as the serializer expects part.type
            self.content = [SimpleNamespace(type="text", text="only part")]
            self.cache = False
            self.tool_calls = False

    am = Assist()
    result = serializer.AnthropicMessageSerializer.serialize(am)
    assert result["role"] == "assistant"
    assert result["content"] == "only part"


def test_serialize_assistant_with_tool_calls_keeps_list(monkeypatch):
    """AssistantMessage with tool calls should append tool blocks and return list content (not simplified)."""
    monkeypatch.setattr(serializer, "UserMessage", type("UserMessageClass", (), {}))
    monkeypatch.setattr(serializer, "SystemMessage", type("SystemMessageClass", (), {}))
    monkeypatch.setattr(serializer, "AssistantMessage", type("AssistantMessageClass", (), {}))

    def fake_serialize_tool_calls_to_content(tool_calls, use_cache):
        assert use_cache is False
        # Return a ToolUseBlock-like dict
        return [ {"type": "tool", "tool_name": "search"} ]

    def fake_message_param(**kwargs):
        return kwargs

    monkeypatch.setattr(
        serializer.AnthropicMessageSerializer, "_serialize_tool_calls_to_content", staticmethod(fake_serialize_tool_calls_to_content)
    )
    monkeypatch.setattr(serializer, "MessageParam", fake_message_param)

    class Assist(serializer.AssistantMessage):
        def __init__(self):
            self.content = None
            self.cache = False
            self.tool_calls = [ {"name": "search"} ]

    am = Assist()
    result = serializer.AnthropicMessageSerializer.serialize(am)
    assert result["role"] == "assistant"
    assert isinstance(result["content"], list)
    assert result["content"][0]["type"] == "tool"
    assert result["content"][0]["tool_name"] == "search"


def test_serialize_unknown_type_raises_value_error(monkeypatch):
    """Passing an object that is not a User/System/Assistant message should raise ValueError."""
    monkeypatch.setattr(serializer, "UserMessage", type("UserMessageClass", (), {}))
    monkeypatch.setattr(serializer, "SystemMessage", type("SystemMessageClass", (), {}))
    monkeypatch.setattr(serializer, "AssistantMessage", type("AssistantMessageClass", (), {}))

    class NotAMessage:
        pass

    with pytest.raises(ValueError) as exc:
        serializer.AnthropicMessageSerializer.serialize(NotAMessage())

    assert "Unknown message type" in str(exc.value)
