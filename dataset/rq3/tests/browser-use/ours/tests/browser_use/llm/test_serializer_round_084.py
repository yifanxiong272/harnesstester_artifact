import types
import pytest

from browser_use.llm.litellm import serializer as ser


class FakeUser:
    def __init__(self, content, name=None):
        self.content = content
        self.name = name


class FakeSystem:
    def __init__(self, content, name=None):
        self.content = content
        self.name = name


class FakeAssistant:
    def __init__(self, content, name=None, tool_calls=None):
        self.content = content
        self.name = name
        # allow both None and empty list to test both branches
        self.tool_calls = tool_calls


def _make_tool_call(id_, fname, args):
    return types.SimpleNamespace(id=id_, function=types.SimpleNamespace(name=fname, arguments=args))


def _patch_serializer_helpers(monkeypatch):
    # Patch the symbol names inside the serializer module so isinstance checks
    # resolve to our fake classes, and patch the content serializers to deterministic values.
    monkeypatch.setattr(ser, "UserMessage", FakeUser, raising=False)
    monkeypatch.setattr(ser, "SystemMessage", FakeSystem, raising=False)
    monkeypatch.setattr(ser, "AssistantMessage", FakeAssistant, raising=False)

    monkeypatch.setattr(
        ser.LiteLLMMessageSerializer,
        "_serialize_user_content",
        staticmethod(lambda content: f"user:{content}"),
        raising=False,
    )
    monkeypatch.setattr(
        ser.LiteLLMMessageSerializer,
        "_serialize_system_content",
        staticmethod(lambda content: f"system:{content}"),
        raising=False,
    )
    monkeypatch.setattr(
        ser.LiteLLMMessageSerializer,
        "_serialize_assistant_content",
        staticmethod(lambda content: f"assistant:{content}"),
        raising=False,
    )


def test_serialize_various_messages_round_084(monkeypatch):
    """Cover user/system/assistant with tool calls present branch and name handling."""
    _patch_serializer_helpers(monkeypatch)

    # Create messages covering multiple branches:
    user = FakeUser(content="hello", name="alice")
    system = FakeSystem(content="sys", name=None)  # name None -> branch where name not added

    tc1 = _make_tool_call("t1", "fn_one", '{"a": 1}')
    tc2 = _make_tool_call("t2", "fn_two", '{"b": 2}')
    assistant = FakeAssistant(content="resp", name="bot", tool_calls=[tc1, tc2])

    out = ser.LiteLLMMessageSerializer.serialize([user, system, assistant])

    # Expect three resulting dicts in same order
    assert isinstance(out, list) and len(out) == 3

    u = out[0]
    assert u["role"] == "user"
    assert u["content"] == "user:hello"
    # name was provided -> included
    assert u["name"] == "alice"

    s = out[1]
    assert s["role"] == "system"
    assert s["content"] == "system:sys"
    # name was None -> not present in dict
    assert "name" not in s

    a = out[2]
    assert a["role"] == "assistant"
    assert a["content"] == "assistant:resp"
    assert a["name"] == "bot"
    # tool_calls present -> should be a list of serialized tool call dicts
    assert "tool_calls" in a and isinstance(a["tool_calls"], list)
    assert len(a["tool_calls"]) == 2

    # Validate shape of the first tool_call entry
    tc0 = a["tool_calls"][0]
    assert tc0["id"] == "t1"
    assert tc0["type"] == "function"
    assert isinstance(tc0["function"], dict)
    assert tc0["function"]["name"] == "fn_one"
    assert tc0["function"]["arguments"] == '{"a": 1}'


def test_serialize_assistant_without_tool_calls_round_084(monkeypatch):
    """Cover assistant branch where tool_calls is empty/falsey and name absent."""
    _patch_serializer_helpers(monkeypatch)

    # Assistant with empty list -> should not include 'tool_calls' key
    assistant_no_tools = FakeAssistant(content="nope", name=None, tool_calls=[])

    out = ser.LiteLLMMessageSerializer.serialize([assistant_no_tools])
    assert isinstance(out, list) and len(out) == 1
    a = out[0]
    assert a["role"] == "assistant"
    assert a["content"] == "assistant:nope"
    # name was None -> not present
    assert "name" not in a
    # empty list is falsey -> should not include tool_calls key
    assert "tool_calls" not in a
