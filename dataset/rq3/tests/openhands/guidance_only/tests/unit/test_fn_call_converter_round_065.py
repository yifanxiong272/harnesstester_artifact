import json
import re
import pytest

from openhands.llm import fn_call_converter as fc


def test_system_list_content_suffix_removed_round_065(monkeypatch):
    # Ensure the system suffix that was appended is removed for list content
    monkeypatch.setattr(fc, "convert_tools_to_description", lambda tools: "DESC")
    monkeypatch.setattr(fc, "SYSTEM_PROMPT_SUFFIX_TEMPLATE", " SUFFIX{description}")

    messages = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "Hello there SUFFIXDESC"}],
        }
    ]

    out = fc.convert_non_fncall_messages_to_fncall_messages(messages, [])
    assert isinstance(out, list)
    assert out[0]["role"] == "system"
    # The suffix (" SUFFIXDESC") should be removed via split(...)[0]
    assert out[0]["content"][-1]["text"] == "Hello there"


def test_user_unexpected_content_type_raises_round_065():
    # A user message with a non-str, non-list content (e.g. int) should raise
    messages = [{"role": "user", "content": 123}]
    with pytest.raises(fc.FunctionCallConversionError):
        fc.convert_non_fncall_messages_to_fncall_messages(messages, [])


def test_assistant_list_fn_not_last_raises_round_065(monkeypatch):
    # Patch FN_REGEX_PATTERN so we control the pattern matching behavior
    monkeypatch.setattr(fc, "FN_REGEX_PATTERN", r"<function=(\w+)>(.*?)</function>")

    # content list where function call text exists but is NOT in the LAST index -> should raise
    messages = [
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "This has a <function=foo>body</function> inside"},
                {"type": "not_text", "meta": "something"},
            ],
        }
    ]

    with pytest.raises(fc.FunctionCallConversionError):
        fc.convert_non_fncall_messages_to_fncall_messages(messages, [])


def test_assistant_fn_call_parses_to_tool_call_round_065(monkeypatch):
    # Setup patterns and helpers so the function call is recognized and parameters are processed
    monkeypatch.setattr(fc, "FN_REGEX_PATTERN", r"<function=(\w+)>(.*?)</function>")
    # normalize and fix stopword are idempotent for this test
    monkeypatch.setattr(fc, "_normalize_parameter_tags", lambda body: body)
    monkeypatch.setattr(fc, "_fix_stopword", lambda s: s)
    # force parameter extraction to a deterministic dict (no regex dependence)
    monkeypatch.setattr(fc, "_extract_and_validate_params", lambda matching_tool, param_matches, fn_name: {"k": "v"})

    # Provide a tools entry that includes the required 'description' key to avoid KeyError
    tools = [
        {
            "type": "function",
            "function": {"name": "doit", "description": "does something"},
        },
    ]

    # assistant message contains a function call in-line — content should be trimmed
    messages = [
        {"role": "assistant", "content": "Before text <function=doit>params</function>"}
    ]

    out = fc.convert_non_fncall_messages_to_fncall_messages(messages, tools)
    # We expect one converted assistant message with a tool_call entry
    assert len(out) == 1
    converted = out[0]
    assert converted["role"] == "assistant"
    assert "tool_calls" in converted and isinstance(converted["tool_calls"], list)
    assert len(converted["tool_calls"]) == 1

    tool_call = converted["tool_calls"][0]
    # tool call should reference the 'doit' function and have JSON args for the returned params
    assert tool_call["function"]["name"] == "doit"
    assert json.loads(tool_call["function"]["arguments"]) == {"k": "v"}
    # The content should have had the '<function=' portion removed and be stripped
    assert converted["content"] == "Before text"


def test_assistant_fn_name_not_in_tools_raises_validation_round_065(monkeypatch):
    # Ensure function regex picks up the name, but the tools list does not contain it
    monkeypatch.setattr(fc, "FN_REGEX_PATTERN", r"<function=(\w+)>(.*?)</function>")
    messages = [{"role": "assistant", "content": "start <function=unknown></function> end"}]

    # tools has a different function name, so validation should fail
    tools = [{"type": "function", "function": {"name": "other", "description": "x"}}]

    with pytest.raises(fc.FunctionCallValidationError):
        fc.convert_non_fncall_messages_to_fncall_messages(messages, tools)
