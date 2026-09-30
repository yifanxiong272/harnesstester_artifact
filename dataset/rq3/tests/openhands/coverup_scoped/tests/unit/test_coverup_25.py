# file: openhands/llm/fn_call_converter.py:481-622
# asked: {"lines": [504, 509, 511, 512, 529, 538, 539, 540, 541, 542, 545, 546, 547, 548, 554, 555, 570, 571, 575, 576, 577, 578, 580, 581, 587, 589, 590, 601, 610, 612, 613, 619, 620], "branches": [[503, 504], [505, 511], [506, 509], [519, 557], [528, 529], [530, 554], [531, 538], [568, 592], [569, 570], [579, 580], [582, 589], [583, 587], [595, 619], [600, 601], [602, 612], [603, 610]]}
# gained: {"lines": [504, 509, 511, 512, 529, 538, 539, 540, 541, 542, 545, 546, 547, 548, 554, 555, 570, 571, 575, 576, 577, 578, 580, 581, 587, 589, 590, 610, 612, 613, 619, 620], "branches": [[503, 504], [505, 511], [506, 509], [519, 557], [528, 529], [530, 554], [531, 538], [569, 570], [579, 580], [582, 589], [583, 587], [595, 619], [602, 612], [603, 610]]}

import pytest
import json

import openhands.llm.fn_call_converter as fnc


@pytest.fixture(autouse=True)
def default_patches(monkeypatch):
    # Provide sane defaults for dependencies used by the converter.
    monkeypatch.setattr(
        fnc,
        "convert_tools_to_description",
        lambda tools: "TOOL_DESC" if tools else "",
        raising=False,
    )
    monkeypatch.setattr(
        fnc,
        "SYSTEM_PROMPT_SUFFIX_TEMPLATE",
        " SUFFIX:{description}",
        raising=False,
    )
    monkeypatch.setattr(
        fnc,
        "IN_CONTEXT_LEARNING_EXAMPLE_PREFIX",
        lambda tools: "EXAMPLE:" if tools else "",
        raising=False,
    )
    monkeypatch.setattr(
        fnc,
        "IN_CONTEXT_LEARNING_EXAMPLE_SUFFIX",
        ":END",
        raising=False,
    )
    # default convert_tool_call_to_string
    monkeypatch.setattr(
        fnc,
        "convert_tool_call_to_string",
        lambda tc: "TOOL_CALL_STR",
        raising=False,
    )
    yield


def test_system_message_appends_suffix_for_list_and_str(monkeypatch):
    # system message with list content (empty -> append)
    messages = [{"role": "system", "content": []}]
    out = fnc.convert_fncall_messages_to_non_fncall_messages(messages, tools=["t1"])
    assert out[0]["role"] == "system"
    assert isinstance(out[0]["content"], list)
    assert out[0]["content"] == [{"type": "text", "text": " SUFFIX:TOOL_DESC"}]

    # system message with string content -> suffix appended
    messages = [{"role": "system", "content": "hello"}]
    out = fnc.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    # tools empty -> description empty string
    assert out[0]["content"] == "hello SUFFIX:"


def test_system_message_unexpected_content_type_raises():
    messages = [{"role": "system", "content": 12345}]
    with pytest.raises(fnc.FunctionCallConversionError) as exc:
        fnc.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    assert "Unexpected content type" in str(exc.value)


def test_user_message_in_context_examples_variations():
    # 1) first user message as string gets example and suffix
    messages = [
        {"role": "user", "content": "ask1"},
        {"role": "user", "content": "ask2"},
    ]
    out = fnc.convert_fncall_messages_to_non_fncall_messages(messages, tools=["t"])
    # Only first user message altered
    assert out[0]["content"] == "EXAMPLE:ask1:END"
    assert out[1]["content"] == "ask2"

    # 2) user message list with first element text
    messages = [{"role": "user", "content": [{"type": "text", "text": "hello"}, {"type": "img", "url": "u"}]}]
    out = fnc.convert_fncall_messages_to_non_fncall_messages(messages, tools=["t"])
    assert out[0]["content"][0]["text"] == "EXAMPLE:hello:END"
    # other parts preserved
    assert out[0]["content"][1]["type"] == "img"

    # 3) user message list with no text at first -> should wrap with example and suffix
    messages = [{"role": "user", "content": [{"type": "img", "url": "u"}]}]
    out = fnc.convert_fncall_messages_to_non_fncall_messages(messages, tools=["t"])
    content = out[0]["content"]
    assert content[0] == {"type": "text", "text": "EXAMPLE:"}
    assert content[1] == {"type": "img", "url": "u"}
    assert content[2] == {"type": "text", "text": ":END"}

    # 4) unexpected content type raises
    messages = [{"role": "user", "content": 999}]
    with pytest.raises(fnc.FunctionCallConversionError):
        fnc.convert_fncall_messages_to_non_fncall_messages(messages, tools=["t"])


def test_assistant_tool_calls_and_errors(monkeypatch):
    # 1) tool_calls length != 1 -> raise
    messages = [{"role": "assistant", "content": "resp", "tool_calls": [{}, {}]}]
    with pytest.raises(fnc.FunctionCallConversionError) as exc:
        fnc.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    assert "Expected exactly one tool call" in str(exc.value)

    # 2) convert_tool_call_to_string raises -> rewrapped error
    def raise_conversion(tc):
        raise fnc.FunctionCallConversionError("inner fail")

    monkeypatch.setattr(fnc, "convert_tool_call_to_string", raise_conversion, raising=False)
    messages = [{"role": "assistant", "content": "resp", "tool_calls": [{"some": "call"}]}]
    with pytest.raises(fnc.FunctionCallConversionError) as exc:
        fnc.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    assert "Failed to convert tool call to string." in str(exc.value)

    # restore convert_tool_call_to_string to default for following cases
    monkeypatch.setattr(fnc, "convert_tool_call_to_string", lambda tc: "CALLX", raising=False)

    # 3) content is str -> appended and lstrip applied
    messages = [{"role": "assistant", "content": "  leading", "tool_calls": [{"some": "call"}]}]
    out = fnc.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    assert out[0]["role"] == "assistant"
    # leading spaces removed
    assert out[0]["content"] == "leading\n\nCALLX"

    # 4) content is list and last element is text -> append tool content and lstrip
    messages = [{"role": "assistant", "content": [{"type": "image", "url": "u"}, {"type": "text", "text": "  tail"}], "tool_calls": [{"some": "call"}]}]
    out = fnc.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    # last element modified and leading whitespace lstripped
    assert out[0]["content"][-1]["text"] == "tail\n\nCALLX"

    # 5) content is list and last element is not text -> new text appended
    messages = [{"role": "assistant", "content": [{"type": "image", "url": "u"}], "tool_calls": [{"some": "call"}]}]
    out = fnc.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    assert out[0]["content"][-1] == {"type": "text", "text": "CALLX"}

    # 6) content type invalid -> raise
    messages = [{"role": "assistant", "content": 123, "tool_calls": [{"some": "call"}]}]
    with pytest.raises(fnc.FunctionCallConversionError) as exc:
        fnc.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    assert "Unexpected content type" in str(exc.value)


def test_tool_messages_various_and_cache_control():
    # 1) list content with first text present -> prefix added to that entry and cache_control set on last element
    messages = [
        {
            "role": "tool",
            "name": "mytool",
            "content": [{"type": "text", "text": "result"}, {"type": "img", "url": "u"}],
            "cache_control": True,
        }
    ]
    out = fnc.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    assert out[0]["role"] == "user"
    content = out[0]["content"]
    assert content[0]["text"].startswith("EXECUTION RESULT of [mytool]:\nresult")
    # cache_control set on last element
    assert content[-1].get("cache_control") == {"type": "ephemeral"}

    # 2) list content with no text -> prefix element inserted at front and cache_control set on last element
    messages = [
        {
            "role": "tool",
            "name": "another",
            "content": [{"type": "img", "url": "u"}],
            "cache_control": True,
        }
    ]
    out = fnc.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    content = out[0]["content"]
    assert content[0] == {"type": "text", "text": "EXECUTION RESULT of [another]:\n"}
    assert content[-1].get("cache_control") == {"type": "ephemeral"}

    # 3) unexpected content type for tool -> raise
    messages = [{"role": "tool", "name": "x", "content": 12}]
    with pytest.raises(fnc.FunctionCallConversionError):
        fnc.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])


def test_unexpected_role_raises():
    messages = [{"role": "unknown", "content": "x"}]
    with pytest.raises(fnc.FunctionCallConversionError) as exc:
        fnc.convert_fncall_messages_to_non_fncall_messages(messages, tools=[])
    assert "Unexpected role" in str(exc.value)
