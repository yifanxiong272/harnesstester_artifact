import pytest

from importlib import import_module

serializer = import_module('browser_use.llm.ollama.serializer')


class FakeMessage:
    def __init__(self, role, content=None):
        self.role = role
        self.content = content
        # optional attributes that the real code may set
        self.images = None
        self.tool_calls = None


def _patch_message_and_helpers(monkeypatch, *, text_return=None, images_return=None, tool_calls_return=None):
    """Helper to monkeypatch Message class and serializer helper methods to deterministic fakes."""
    # Patch the Message class used inside the serializer module so we can observe assignments
    monkeypatch.setattr(serializer, 'Message', FakeMessage, raising=True)

    # Patch the static helper methods on OllamaMessageSerializer
    if text_return is not None:
        monkeypatch.setattr(
            serializer.OllamaMessageSerializer,
            '_extract_text_content',
            staticmethod(lambda content: text_return),
            raising=True,
        )
    if images_return is not None:
        monkeypatch.setattr(
            serializer.OllamaMessageSerializer,
            '_extract_images',
            staticmethod(lambda content: images_return),
            raising=True,
        )
    if tool_calls_return is not None:
        monkeypatch.setattr(
            serializer.OllamaMessageSerializer,
            '_serialize_tool_calls',
            staticmethod(lambda tc: tool_calls_return),
            raising=True,
        )


def test_user_message_with_text_and_images_round_111(monkeypatch):
    # Prepare deterministic patches: text content and images present
    _patch_message_and_helpers(monkeypatch, text_return='hello user', images_return=['img1', 'img2'])

    # Create a lightweight fake UserMessage class and instance for isinstance checks
    class FakeUserMessage:
        def __init__(self, content):
            self.content = content

    monkeypatch.setattr(serializer, 'UserMessage', FakeUserMessage, raising=True)

    msg = FakeUserMessage(content='irrelevant')

    result = serializer.OllamaMessageSerializer.serialize(msg)

    # Assertions: role, content, and images assigned
    assert isinstance(result, FakeMessage)
    assert result.role == 'user'
    assert result.content == 'hello user'
    assert result.images == ['img1', 'img2']


def test_user_message_without_text_and_no_images_round_111(monkeypatch):
    # Both helpers return falsy values -> content should become None and images not set
    _patch_message_and_helpers(monkeypatch, text_return='', images_return=[])

    class FakeUserMessage:
        def __init__(self, content):
            self.content = content

    monkeypatch.setattr(serializer, 'UserMessage', FakeUserMessage, raising=True)

    msg = FakeUserMessage(content='no text here')

    result = serializer.OllamaMessageSerializer.serialize(msg)

    assert isinstance(result, FakeMessage)
    assert result.role == 'user'
    # When text content is falsy the serializer sets content to None
    assert result.content is None
    # images should remain default (None) because empty list is falsy for the branch
    assert result.images in (None, [])


def test_system_message_text_round_111(monkeypatch):
    # System message branch: should produce role 'system' and return content when present
    _patch_message_and_helpers(monkeypatch, text_return='system notice')

    class FakeSystemMessage:
        def __init__(self, content):
            self.content = content

    monkeypatch.setattr(serializer, 'SystemMessage', FakeSystemMessage, raising=True)

    msg = FakeSystemMessage(content='ignored')

    result = serializer.OllamaMessageSerializer.serialize(msg)

    assert isinstance(result, FakeMessage)
    assert result.role == 'system'
    assert result.content == 'system notice'


def test_assistant_message_with_tool_calls_and_no_content_round_111(monkeypatch):
    # Assistant branch: no textual content but tool_calls truthy should result in tool_calls assigned
    _patch_message_and_helpers(monkeypatch, text_return=None, tool_calls_return=['serialized_call'])

    class FakeAssistantMessage:
        def __init__(self, content=None, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls

    monkeypatch.setattr(serializer, 'AssistantMessage', FakeAssistantMessage, raising=True)

    # content is None, tool_calls is truthy -> triggers tool_calls serialization branch
    msg = FakeAssistantMessage(content=None, tool_calls=['call1'])

    result = serializer.OllamaMessageSerializer.serialize(msg)

    assert isinstance(result, FakeMessage)
    assert result.role == 'assistant'
    # No text content -> serializer should set content to None
    assert result.content is None
    # tool_calls should be assigned from our patched _serialize_tool_calls
    assert result.tool_calls == ['serialized_call']


def test_unknown_message_raises_round_111():
    # Passing an object that is not an instance of UserMessage/SystemMessage/AssistantMessage
    # should raise the ValueError branch for unknown types
    with pytest.raises(ValueError) as exc:
        serializer.OllamaMessageSerializer.serialize(object())

    # The error message should include the runtime type of the passed object
    assert "Unknown message type" in str(exc.value)
    assert "object" in str(exc.value)
