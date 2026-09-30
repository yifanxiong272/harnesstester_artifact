import pytest

from openhands.llm import fn_call_converter as mod
from openhands.core.exceptions import FunctionCallConversionError

convert = mod.convert_fncall_messages_to_non_fncall_messages


def test_system_content_str_round_048():
    # system content as str should be appended with the system prompt suffix
    messages = [{"role": "system", "content": "ORIG"}]
    tools = []
    out = convert(messages, tools, add_in_context_learning_example=False)
    assert out[0]["role"] == "system"
    assert isinstance(out[0]["content"], str)
    assert out[0]["content"].startswith("ORIG")
    assert len(out[0]["content"]) > len("ORIG")


def test_system_content_list_text_round_048():
    # system content as list with last element type 'text' should have its text extended
    messages = [{
        "role": "system",
        "content": [
            {"type": "meta", "x": 1},
            {"type": "text", "text": "hello"},
        ],
    }]
    tools = []
    out = convert(messages, tools, add_in_context_learning_example=False)
    assert out[0]["role"] == "system"
    content = out[0]["content"]
    assert isinstance(content, list)
    assert content[-1]["type"] == "text"
    assert content[-1]["text"].startswith("hello")
    assert len(content[-1]["text"]) > len("hello")


def test_system_content_list_append_new_text_round_048():
    # system content list whose last element is not 'text' should get a new text element appended
    messages = [{
        "role": "system",
        "content": [{"type": "other", "foo": 1}],
    }]
    tools = []
    out = convert(messages, tools, add_in_context_learning_example=False)
    assert out[0]["role"] == "system"
    content = out[0]["content"]
    assert isinstance(content, list)
    assert content[-1].get("type") == "text"
    assert isinstance(content[-1].get("text"), str)


def test_system_content_invalid_type_raises_round_048():
    # system content with unexpected type should raise a FunctionCallConversionError
    messages = [{"role": "system", "content": 123}]
    with pytest.raises(FunctionCallConversionError):
        convert(messages, [])


def test_user_add_in_context_example_str_round_048(monkeypatch):
    # When IN_CONTEXT_LEARNING_EXAMPLE_PREFIX returns an example, a string user content should be prefixed/suffixed
    monkeypatch.setattr(mod, "IN_CONTEXT_LEARNING_EXAMPLE_PREFIX", lambda tools: "EXAMPLE_")
    monkeypatch.setattr(mod, "IN_CONTEXT_LEARNING_EXAMPLE_SUFFIX", "_SUFF")
    messages = [{"role": "user", "content": "body"}]
    out = convert(messages, [], add_in_context_learning_example=True)
    assert out[0]["role"] == "user"
    assert out[0]["content"] == "EXAMPLE_" + "body" + "_SUFF"


def test_user_add_in_context_example_list_first_text_round_048(monkeypatch):
    # user content as list and first element 'text' should have its text modified
    monkeypatch.setattr(mod, "IN_CONTEXT_LEARNING_EXAMPLE_PREFIX", lambda tools: "P_")
    monkeypatch.setattr(mod, "IN_CONTEXT_LEARNING_EXAMPLE_SUFFIX", "_S")
    messages = [{"role": "user", "content": [{"type": "text", "text": "hello"}, {"type": "meta"}]}]
    out = convert(messages, [], add_in_context_learning_example=True)
    assert out[0]["role"] == "user"
    content = out[0]["content"]
    assert content[0]["text"] == "P_" + "hello" + "_S"


def test_user_add_in_context_example_list_first_nontext_round_048(monkeypatch):
    # user content as list with first element not 'text' should result in new example and suffix entries around original list
    monkeypatch.setattr(mod, "IN_CONTEXT_LEARNING_EXAMPLE_PREFIX", lambda tools: "BEG_")
    monkeypatch.setattr(mod, "IN_CONTEXT_LEARNING_EXAMPLE_SUFFIX", "_END")
    original = [{"type": "meta", "v": 1}]
    messages = [{"role": "user", "content": original}]
    out = convert(messages, [], add_in_context_learning_example=True)
    assert out[0]["role"] == "user"
    content = out[0]["content"]
    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[0]["text"].startswith("BEG_")
    assert content[-1]["type"] == "text"
    assert content[-1]["text"] == "_END"


def test_user_invalid_content_raises_round_048(monkeypatch):
    # Ensure IN_CONTEXT_LEARNING_EXAMPLE_PREFIX returns a truthy example so the invalid-content branch is exercised
    monkeypatch.setattr(mod, "IN_CONTEXT_LEARNING_EXAMPLE_PREFIX", lambda tools: "EX_")
    monkeypatch.setattr(mod, "IN_CONTEXT_LEARNING_EXAMPLE_SUFFIX", "_SUF")
    messages = [{"role": "user", "content": 999}]
    with pytest.raises(FunctionCallConversionError):
        convert(messages, [], add_in_context_learning_example=True)


def test_assistant_multiple_tool_calls_raises_round_048():
    # assistant with multiple tool_calls should raise
    messages = [{
        "role": "assistant",
        "content": "c",
        "tool_calls": [{}, {}],
    }]
    with pytest.raises(FunctionCallConversionError):
        convert(messages, [])


def test_assistant_tool_call_conversion_error_round_048(monkeypatch):
    # If convert_tool_call_to_string raises, the conversion should raise and include context
    def _raiser(tc):
        raise FunctionCallConversionError("inner failure")

    monkeypatch.setattr(mod, "convert_tool_call_to_string", _raiser)
    messages = [{
        "role": "assistant",
        "content": "c",
        "tool_calls": [{"name": "t1"}],
    }]
    with pytest.raises(FunctionCallConversionError) as ei:
        convert(messages, [])
    assert "Failed to convert tool call to string." in str(ei.value)


def test_assistant_tool_call_append_str_and_list_round_048(monkeypatch):
    # Normal conversion of a single tool_call should append the tool string to content (str and list text case)
    monkeypatch.setattr(mod, "convert_tool_call_to_string", lambda tc: "TOOL_STR")
    # string content case: leading spaces must be stripped after appending
    messages = [{
        "role": "assistant",
        "content": "  leading",
        "tool_calls": [{"name": "t1"}],
    }]
    out = convert(messages, [])
    assert out[0]["role"] == "assistant"
    assert out[0]["content"] == "leading\n\nTOOL_STR"

    # list content where last element is text: last text should be appended and lstripped
    messages = [{
        "role": "assistant",
        "content": [{"type": "meta"}, {"type": "text", "text": "  bye"}],
        "tool_calls": [{"name": "t1"}],
    }]
    out = convert(messages, [])
    assert out[0]["content"][-1]["text"] == "bye\n\nTOOL_STR"


def test_assistant_tool_call_append_list_nontext_round_048(monkeypatch):
    # list content where last element is not text should get a new text element appended
    monkeypatch.setattr(mod, "convert_tool_call_to_string", lambda tc: "X")
    messages = [{
        "role": "assistant",
        "content": [{"type": "meta"}],
        "tool_calls": [{"name": "t1"}],
    }]
    out = convert(messages, [])
    assert out[0]["content"][-1]["type"] == "text"
    assert out[0]["content"][-1]["text"] == "X"


def test_tool_content_str_round_048():
    # tool role with string content should be converted to a user role and prefixed
    messages = [{"role": "tool", "name": "mytool", "content": "RESULT"}]
    out = convert(messages, [])
    assert out[0]["role"] == "user"
    assert isinstance(out[0]["content"], str)
    assert out[0]["content"].startswith("EXECUTION RESULT of [mytool]:\n")
    assert out[0]["content"].endswith("RESULT")


def test_tool_content_list_first_text_and_cachecontrol_round_048():
    # tool role with list content containing a text entry should have that text prefixed
    messages = [{
        "role": "tool",
        "name": "toolA",
        "content": [{"type": "meta"}, {"type": "text", "text": "orig"}],
        # include cache_control to trigger addition of ephemeral flag on last element
        "cache_control": True,
    }]
    out = convert(messages, [])
    assert out[0]["role"] == "user"
    content = out[0]["content"]
    # first text element should have been prefixed
    found = next((c for c in content if c.get("type") == "text"), None)
    assert found is not None
    assert found["text"].startswith("EXECUTION RESULT of [toolA]:\n")
    # last element should have cache_control set
    assert content[-1].get("cache_control") == {"type": "ephemeral"}


def test_tool_content_list_no_text_add_and_cachecontrol_round_048():
    # tool role with list content but no text entries should get a text element prefixed and cache_control set
    messages = [{
        "role": "tool",
        "name": "toolB",
        "content": [{"type": "meta"}],
        "cache_control": True,
    }]
    out = convert(messages, [])
    content = out[0]["content"]
    assert content[0]["type"] == "text"
    assert content[0]["text"].startswith("EXECUTION RESULT of [toolB]:\n")
    assert content[-1].get("cache_control") == {"type": "ephemeral"}


def test_unknown_role_raises_round_048():
    # any unknown role should raise
    messages = [{"role": "bogus", "content": "x"}]
    with pytest.raises(FunctionCallConversionError):
        convert(messages, [])
