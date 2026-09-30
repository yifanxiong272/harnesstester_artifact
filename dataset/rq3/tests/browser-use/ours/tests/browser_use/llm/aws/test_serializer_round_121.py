import pytest

import browser_use.llm.aws.serializer as serializer


# The tests monkeypatch the message classes and the helper serialization
# functions inside the serializer module so we can deterministically drive
# the different branches of AWSBedrockMessageSerializer.serialize.


def test_serialize_user_message_round_121(monkeypatch):
    class DummyUser:
        def __init__(self, content):
            self.content = content

    # Patch the symbol the serializer checks with our dummy class
    monkeypatch.setattr(serializer, "UserMessage", DummyUser, raising=False)

    # Make the helper deterministic
    monkeypatch.setattr(
        serializer.AWSBedrockMessageSerializer,
        "_serialize_user_content",
        staticmethod(lambda content: [{"text": f"u:{content}"}]),
        raising=False,
    )

    msg = DummyUser("hello")
    out = serializer.AWSBedrockMessageSerializer.serialize(msg)

    assert out == {"role": "user", "content": [{"text": "u:hello"}]}


def test_serialize_system_message_round_121(monkeypatch):
    class DummySystem:
        def __init__(self, sentinel):
            self.sentinel = sentinel

    monkeypatch.setattr(serializer, "SystemMessage", DummySystem, raising=False)

    instance = DummySystem(sentinel=object())

    # SystemMessage branch should return the message object unchanged
    res = serializer.AWSBedrockMessageSerializer.serialize(instance)
    assert res is instance


def test_serialize_assistant_no_content_no_tool_calls_round_121(monkeypatch):
    class DummyAssistant:
        def __init__(self, content=None, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls if tool_calls is not None else []

    monkeypatch.setattr(serializer, "AssistantMessage", DummyAssistant, raising=False)

    # When content is None and there are no tool_calls, AWS expects a single blank block
    msg = DummyAssistant(content=None, tool_calls=[])
    out = serializer.AWSBedrockMessageSerializer.serialize(msg)

    assert out["role"] == "assistant"
    # Should provide the required empty content block
    assert out["content"] == [{"text": ""}]


def test_serialize_assistant_with_content_and_tool_calls_round_121(monkeypatch):
    class DummyAssistant:
        def __init__(self, content=None, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls if tool_calls is not None else []

    class DummyToolCall:
        def __init__(self, name):
            self.name = name

    monkeypatch.setattr(serializer, "AssistantMessage", DummyAssistant, raising=False)

    # Patch assistant content serialization to return a list of blocks
    monkeypatch.setattr(
        serializer.AWSBedrockMessageSerializer,
        "_serialize_assistant_content",
        staticmethod(lambda content: [{"text": f"assistant:{content}"}]),
        raising=False,
    )

    # Patch tool call serialization to return a dict per tool call
    monkeypatch.setattr(
        serializer.AWSBedrockMessageSerializer,
        "_serialize_tool_call",
        staticmethod(lambda tool_call: {"tool": tool_call.name}),
        raising=False,
    )

    msg = DummyAssistant(content="c1", tool_calls=[DummyToolCall("t1")])
    out = serializer.AWSBedrockMessageSerializer.serialize(msg)

    assert out["role"] == "assistant"
    # Expect assistant content block first, then tool call block appended
    assert out["content"] == [{"text": "assistant:c1"}, {"tool": "t1"}]


def test_serialize_unknown_type_raises_round_121(monkeypatch):
    # Define some unrelated classes and patch the serializer to use them
    class UM:
        pass

    class SM:
        pass

    class AM:
        pass

    monkeypatch.setattr(serializer, "UserMessage", UM, raising=False)
    monkeypatch.setattr(serializer, "SystemMessage", SM, raising=False)
    monkeypatch.setattr(serializer, "AssistantMessage", AM, raising=False)

    class Other:
        pass

    with pytest.raises(ValueError) as exc:
        serializer.AWSBedrockMessageSerializer.serialize(Other())

    # Error should mention the unknown type
    assert "Unknown message type" in str(exc.value)
