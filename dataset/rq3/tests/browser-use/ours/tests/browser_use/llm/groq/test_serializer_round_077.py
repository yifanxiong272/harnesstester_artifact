import pytest

import browser_use.llm.groq.serializer as serializer


# Lightweight stand-ins for the message classes the serializer checks with isinstance.
class DummyUser:
    def __init__(self, content, name=None):
        self.content = content
        self.name = name


class DummySystem:
    def __init__(self, content, name=None):
        self.content = content
        self.name = name


class DummyAssistant:
    def __init__(self, content=None, name=None, tool_calls=None):
        self.content = content
        self.name = name
        # tool_calls should be truthy/falsey; actual elements are passed to _serialize_tool_call
        self.tool_calls = list(tool_calls) if tool_calls is not None else []


def test_user_with_and_without_name_round_077(monkeypatch):
    # Patch module-level type names so isinstance checks in serializer.resolve to our dummies
    monkeypatch.setattr(serializer, "UserMessage", DummyUser, raising=False)

    # Patch the content serializer to produce a deterministic, observable value
    monkeypatch.setattr(
        serializer.GroqMessageSerializer,
        "_serialize_user_content",
        staticmethod(lambda content: f"SER_USER:{content}"),
        raising=True,
    )

    # With name present: expect 'name' key
    u_with_name = DummyUser(content="hello", name="alice")
    out = serializer.GroqMessageSerializer.serialize(u_with_name)
    assert out["role"] == "user"
    assert out["content"] == "SER_USER:hello"
    assert out["name"] == "alice"

    # Without name: 'name' key should be absent
    u_no_name = DummyUser(content="no_name", name=None)
    out2 = serializer.GroqMessageSerializer.serialize(u_no_name)
    assert out2["role"] == "user"
    assert out2["content"] == "SER_USER:no_name"
    assert "name" not in out2


def test_system_with_and_without_name_round_077(monkeypatch):
    monkeypatch.setattr(serializer, "SystemMessage", DummySystem, raising=False)

    monkeypatch.setattr(
        serializer.GroqMessageSerializer,
        "_serialize_system_content",
        staticmethod(lambda content: f"SER_SYS:{content}"),
        raising=True,
    )

    s_with_name = DummySystem(content="sysc", name="sysname")
    out = serializer.GroqMessageSerializer.serialize(s_with_name)
    assert out["role"] == "system"
    assert out["content"] == "SER_SYS:sysc"
    assert out["name"] == "sysname"

    s_no_name = DummySystem(content="onlysys", name=None)
    out2 = serializer.GroqMessageSerializer.serialize(s_no_name)
    assert out2["role"] == "system"
    assert out2["content"] == "SER_SYS:onlysys"
    assert "name" not in out2


def test_assistant_content_name_and_tool_calls_round_077(monkeypatch):
    # Cover branches where content is None (do not add), and when content present (add),
    # name present/absent, and tool_calls present
    monkeypatch.setattr(serializer, "AssistantMessage", DummyAssistant, raising=False)

    # Case A: content is None -> serializer must not call _serialize_assistant_content and result has only role
    called = {"assisted": False}

    def fail_if_called(content):
        called["assisted"] = True
        raise AssertionError("_serialize_assistant_content should not be called for None content")

    monkeypatch.setattr(
        serializer.GroqMessageSerializer,
        "_serialize_assistant_content",
        staticmethod(fail_if_called),
        raising=True,
    )

    a_none = DummyAssistant(content=None, name=None, tool_calls=[])
    out_none = serializer.GroqMessageSerializer.serialize(a_none)
    assert out_none == {"role": "assistant"}
    assert called["assisted"] is False

    # Case B: content present, name present, tool_calls present
    monkeypatch.setattr(
        serializer.GroqMessageSerializer,
        "_serialize_assistant_content",
        staticmethod(lambda content: {"content_serialized": content + ":AS"}),
        raising=True,
    )

    # Each tool call element should be passed to _serialize_tool_call; return a predictable dict per element
    def serialize_tool_call(tc):
        return {"tool_called_with": tc}

    monkeypatch.setattr(
        serializer.GroqMessageSerializer,
        "_serialize_tool_call",
        staticmethod(serialize_tool_call),
        raising=True,
    )

    a_full = DummyAssistant(content="assist-c", name="the-assistant", tool_calls=["t1", "t2"])
    out_full = serializer.GroqMessageSerializer.serialize(a_full)

    # Assertions covering branches: content added, name added, tool_calls transformed into list
    assert out_full["role"] == "assistant"
    assert out_full["content"] == {"content_serialized": "assist-c:AS"}
    assert out_full["name"] == "the-assistant"
    assert out_full["tool_calls"] == [
        {"tool_called_with": "t1"},
        {"tool_called_with": "t2"},
    ]


def test_unknown_message_type_raises_round_077():
    # An object of an unrelated type should trigger the ValueError branch
    class SomethingElse:
        pass

    with pytest.raises(ValueError) as excinfo:
        serializer.GroqMessageSerializer.serialize(SomethingElse())

    assert "Unknown message type" in str(excinfo.value)
