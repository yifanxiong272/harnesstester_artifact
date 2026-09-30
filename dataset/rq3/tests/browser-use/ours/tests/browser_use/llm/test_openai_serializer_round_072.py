import pytest

from browser_use.llm.openai import serializer as serializer_mod
from browser_use.llm.openai.serializer import OpenAIMessageSerializer

# Create simple fake message classes to patch into the serializer module so
# isinstance checks in OpenAIMessageSerializer.serialize succeed without
# depending on the real browser_use.llm.messages constructors or pydantic.
class FakeUserMessage:
    def __init__(self, content, name=None):
        self.content = content
        self.name = name

class FakeSystemMessage:
    def __init__(self, content, name=None):
        self.content = content
        self.name = name

class FakeAssistantMessage:
    def __init__(self, content=None, name=None, refusal=None, tool_calls=None):
        self.content = content
        self.name = name
        self.refusal = refusal
        self.tool_calls = tool_calls


def _patch_helpers(monkeypatch, *, user_ret="U_CONV", system_ret="S_CONV", assistant_ret="A_CONV", tool_ret=lambda tc: {"tc": tc}):
    """Patch the serializer helper methods to deterministic, inspectable stand-ins.

    We patch the methods on the OpenAIMessageSerializer class object where the
    serialize function resolves them.
    """
    monkeypatch.setattr(serializer_mod, 'UserMessage', FakeUserMessage)
    monkeypatch.setattr(serializer_mod, 'SystemMessage', FakeSystemMessage)
    monkeypatch.setattr(serializer_mod, 'AssistantMessage', FakeAssistantMessage)

    # Patch serialization helpers as staticmethods so calls inside serialize are deterministic
    monkeypatch.setattr(OpenAIMessageSerializer, '_serialize_user_content', staticmethod(lambda c: user_ret))
    monkeypatch.setattr(OpenAIMessageSerializer, '_serialize_system_content', staticmethod(lambda c: system_ret))
    monkeypatch.setattr(OpenAIMessageSerializer, '_serialize_assistant_content', staticmethod(lambda c: assistant_ret))
    monkeypatch.setattr(OpenAIMessageSerializer, '_serialize_tool_call', staticmethod(lambda tc: tool_ret(tc)))


def test_serialize_user_with_and_without_name_round_072(monkeypatch):
    _patch_helpers(monkeypatch, user_ret="user-serialized")

    # User without name: no 'name' key expected
    user_no_name = FakeUserMessage(content="hello", name=None)
    res = OpenAIMessageSerializer.serialize(user_no_name)
    assert res['role'] == 'user'
    assert res['content'] == "user-serialized"
    assert 'name' not in res

    # User with name: name key should be present and preserved
    user_with_name = FakeUserMessage(content="hello2", name="alice")
    res2 = OpenAIMessageSerializer.serialize(user_with_name)
    assert res2['role'] == 'user'
    assert res2['content'] == "user-serialized"
    assert res2['name'] == 'alice'


def test_serialize_system_with_and_without_name_round_072(monkeypatch):
    _patch_helpers(monkeypatch, system_ret="system-serialized")

    sys_no_name = FakeSystemMessage(content="sys", name=None)
    r = OpenAIMessageSerializer.serialize(sys_no_name)
    assert r['role'] == 'system'
    assert r['content'] == 'system-serialized'
    assert 'name' not in r

    sys_with_name = FakeSystemMessage(content="sys2", name='root')
    r2 = OpenAIMessageSerializer.serialize(sys_with_name)
    assert r2['role'] == 'system'
    assert r2['content'] == 'system-serialized'
    assert r2['name'] == 'root'


def test_serialize_assistant_various_round_072(monkeypatch):
    # Patch assistant content and tool serialization deterministically
    _patch_helpers(monkeypatch, assistant_ret={'parts': ['x']}, tool_ret=lambda tc: {'tool_serialized': tc})

    # 1) Assistant with no content, no name/refusal/tool_calls -> only role expected
    assistant_min = FakeAssistantMessage(content=None, name=None, refusal=None, tool_calls=None)
    out_min = OpenAIMessageSerializer.serialize(assistant_min)
    assert out_min == {'role': 'assistant'}

    # 2) Assistant with content => 'content' key present
    assistant_with_content = FakeAssistantMessage(content='some content')
    out_content = OpenAIMessageSerializer.serialize(assistant_with_content)
    assert out_content['role'] == 'assistant'
    assert out_content['content'] == {'parts': ['x']}

    # 3) Assistant with name and refusal
    assistant_full = FakeAssistantMessage(content='c', name='bot', refusal={'reason': 'none'}, tool_calls=[1, 2])
    out_full = OpenAIMessageSerializer.serialize(assistant_full)
    # content should be present
    assert out_full['content'] == {'parts': ['x']}
    # name and refusal must be preserved
    assert out_full['name'] == 'bot'
    assert out_full['refusal'] == {'reason': 'none'}
    # tool_calls should be a list of serialized tool calls
    assert isinstance(out_full['tool_calls'], list)
    assert out_full['tool_calls'] == [{'tool_serialized': 1}, {'tool_serialized': 2}]


def test_serialize_unknown_type_raises_round_072():
    # If an object that's not recognized is passed in, we expect ValueError.
    with pytest.raises(ValueError) as exc:
        OpenAIMessageSerializer.serialize(object())
    assert 'Unknown message type' in str(exc.value)
