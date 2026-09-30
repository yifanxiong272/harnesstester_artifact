# file: openhands/llm/fn_call_converter.py:730-933
# asked: {"lines": [772, 773, 789, 790, 813, 814, 823, 824, 826, 827, 828, 841, 860, 867, 868, 871, 872, 889, 890, 918, 919, 930, 931], "branches": [[753, 759], [754, 759], [771, 772], [775, 789], [777, 776], [780, 782], [782, 776], [798, 813], [818, 826], [822, 823], [826, 827], [826, 831], [849, 930], [853, 871], [854, 860], [866, 867], [888, 889], [915, 918]]}
# gained: {"lines": [772, 773, 789, 790, 813, 814, 826, 841, 860, 867, 868, 871, 872, 889, 890, 930, 931], "branches": [[771, 772], [775, 789], [777, 776], [798, 813], [818, 826], [826, 831], [849, 930], [853, 871], [854, 860], [866, 867], [888, 889]]}

import json
import re
import types
import pytest

from openhands.llm import fn_call_converter as fcc
from openhands.core.exceptions import FunctionCallConversionError, FunctionCallValidationError


def setup_basic_monkeypatch(monkeypatch):
    # Make sure basic helpers behave predictably for tests
    monkeypatch.setattr(fcc, "convert_tools_to_description", lambda tools: "DESC")
    monkeypatch.setattr(fcc, "SYSTEM_PROMPT_SUFFIX_TEMPLATE", " SUFFIX:{description}")
    monkeypatch.setattr(fcc, "IN_CONTEXT_LEARNING_EXAMPLE_PREFIX", lambda tools: "PREFIX:")
    monkeypatch.setattr(fcc, "IN_CONTEXT_LEARNING_EXAMPLE_SUFFIX", "<SUFFIX>")
    # Tool result regex: [tool:NAME]RESULT[/tool]
    monkeypatch.setattr(fcc, "TOOL_RESULT_REGEX_PATTERN", r"\[tool:(\w+)\](.*?)\[/tool\]")
    # Function regex: <function=NAME>(BODY)</function>
    monkeypatch.setattr(fcc, "FN_REGEX_PATTERN", r"<function=(\w+)>(.*?)</function>")
    # Params regex: key="value" or key=123 etc (we will not rely heavily on parsing)
    monkeypatch.setattr(fcc, "FN_PARAM_REGEX_PATTERN", r"(\w+)\s*=\s*\"?(.*?)\"?(?=\s|$)")
    # Basic helpers
    monkeypatch.setattr(fcc, "_fix_stopword", lambda t: t)
    monkeypatch.setattr(fcc, "_normalize_parameter_tags", lambda body: body)
    # Default extractor returns empty dict (valid)
    monkeypatch.setattr(fcc, "_extract_and_validate_params", lambda matching_tool, param_matches, fn_name: {})


def test_system_message_list_suffix_removed(monkeypatch):
    setup_basic_monkeypatch(monkeypatch)
    # Content is list and last item type == 'text' -> should remove suffix portion
    suffix = fcc.SYSTEM_PROMPT_SUFFIX_TEMPLATE.format(description="DESC")
    content = [{"type": "meta", "value": 1}, {"type": "text", "text": "HELLO" + suffix + "TRAIL"}]
    messages = [{"role": "system", "content": content}]
    out = fcc.convert_non_fncall_messages_to_fncall_messages(messages, [])
    assert out[0]["role"] == "system"
    # last text should have suffix part removed
    assert out[0]["content"][-1]["text"] == "HELLO"


def test_user_in_context_prefix_and_suffix_str_removed(monkeypatch):
    setup_basic_monkeypatch(monkeypatch)
    # First user message should have prefix and suffix removed when content is str
    msg = "PREFIX:What is X?<SUFFIX>"
    messages = [{"role": "user", "content": msg}]
    out = fcc.convert_non_fncall_messages_to_fncall_messages(messages, [])
    assert out[0]["role"] == "user"
    assert out[0]["content"] == "What is X?"


def test_user_in_context_prefix_and_suffix_list_removed(monkeypatch):
    setup_basic_monkeypatch(monkeypatch)
    # List content: item with type 'text' startswith prefix and endswith suffix
    content = [{"type": "text", "text": "PREFIX:Tell me<SUFFIX>"}, {"type": "meta", "x": 5}]
    messages = [{"role": "user", "content": content}]
    out = fcc.convert_non_fncall_messages_to_fncall_messages(messages, [])
    assert out[0]["role"] == "user"
    assert out[0]["content"][0]["text"] == "Tell me"


def test_user_in_context_unexpected_content_type_raises(monkeypatch):
    setup_basic_monkeypatch(monkeypatch)
    # First user message with a non-str and non-list content should raise 789-790
    messages = [{"role": "user", "content": 123}]
    with pytest.raises(FunctionCallConversionError) as exc:
        fcc.convert_non_fncall_messages_to_fncall_messages(messages, [])
    assert "Unexpected content type" in str(exc.value)


def test_user_tool_result_string_and_list(monkeypatch):
    setup_basic_monkeypatch(monkeypatch)
    # Ensure first user message is present to set the internal flag (so second is treated as non-first)
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "user", "content": "[tool:search]result text[/tool]"},
    ]
    out = fcc.convert_non_fncall_messages_to_fncall_messages(messages, [])
    # The tool message should be generated for the second message
    assert any(m["role"] == "tool" for m in out)
    tool_msg = next(m for m in out if m["role"] == "tool")
    assert tool_msg["name"] == "search"
    assert tool_msg["content"] == "result text" or (
        isinstance(tool_msg["content"], list) and tool_msg["content"][0]["text"] == "result text"
    )
    # Check correct tool_call_id formatting (toolu_00 because counter starts at 1 and uses -1)
    assert tool_msg["tool_call_id"].startswith("toolu_0")


def test_user_tool_result_list_item(monkeypatch):
    setup_basic_monkeypatch(monkeypatch)
    messages = [
        {"role": "user", "content": "First"},
        {
            "role": "user",
            "content": [
                {"type": "meta", "x": 1},
                {"type": "text", "text": "prefix [tool:calc]42[/tool] suffix"},
            ],
        },
    ]
    out = fcc.convert_non_fncall_messages_to_fncall_messages(messages, [])
    tool_msgs = [m for m in out if m["role"] == "tool"]
    assert tool_msgs, "Expected a tool message to be created from list content"
    tm = tool_msgs[0]
    assert tm["name"] == "calc"
    # content in list-branch should be a list of dicts with text
    assert isinstance(tm["content"], list) and tm["content"][0]["text"] == "42"


def test_user_non_str_non_list_tool_result_raises_813(monkeypatch):
    setup_basic_monkeypatch(monkeypatch)
    # First message to set flag, second is wrong-type content (non-str, non-list) to trigger 813-814
    messages = [{"role": "user", "content": "ok"}, {"role": "user", "content": 999}]
    with pytest.raises(FunctionCallConversionError) as exc:
        fcc.convert_non_fncall_messages_to_fncall_messages(messages, [])
    assert "Unexpected content type" in str(exc.value)


def test_assistant_list_fn_match_not_last_item_raises(monkeypatch):
    setup_basic_monkeypatch(monkeypatch)
    # Create assistant content where last item is not text, but earlier item contains a function call
    content = [
        {"type": "text", "text": "<function=doit>()</function>"},  # matches FN_REGEX_PATTERN
        {"type": "meta", "info": "not text"},  # last is not text -> fn_match will be None but fn_match_exists True -> raise
    ]
    messages = [{"role": "assistant", "content": content}]
    with pytest.raises(FunctionCallConversionError) as exc:
        fcc.convert_non_fncall_messages_to_fncall_messages(messages, [])
    assert "Expecting function call in the LAST index of content list" in str(exc.value)


def test_assistant_unexpected_content_type_raises_871(monkeypatch):
    setup_basic_monkeypatch(monkeypatch)
    # Assistant content with unexpected type (not str/list) should raise at 871-872
    messages = [{"role": "assistant", "content": 3.1415}]
    with pytest.raises(FunctionCallConversionError) as exc:
        fcc.convert_non_fncall_messages_to_fncall_messages(messages, [])
    assert "Unexpected content type" in str(exc.value)


def test_assistant_fn_validation_missing_tool_raises(monkeypatch):
    setup_basic_monkeypatch(monkeypatch)
    # Provide assistant message with a function call for a function not in tools -> triggers FunctionCallValidationError (889-890)
    content = "<function=unknown>{}</function>"
    messages = [{"role": "assistant", "content": content}]
    # Tools list empty -> matching_tool will be None
    with pytest.raises(FunctionCallValidationError) as exc:
        fcc.convert_non_fncall_messages_to_fncall_messages(messages, [])
    assert "Function 'unknown' not found" in str(exc.value)


def test_assistant_fn_call_parsing_and_tool_call_created(monkeypatch):
    setup_basic_monkeypatch(monkeypatch)
    # Setup tools to include the function 'sum'
    tools = [
        {"type": "function", "function": {"name": "sum", "parameters": {}}},
    ]
    # Ensure extract returns expected params for this test
    monkeypatch.setattr(fcc, "_extract_and_validate_params", lambda matching_tool, param_matches, fn_name: {"a": 1})
    # Assistant content with function call in a string (not list) so branch at 915 is used
    content = "Some text before <function=sum>a=1</function>   "
    messages = [{"role": "assistant", "content": content}]
    out = fcc.convert_non_fncall_messages_to_fncall_messages(messages, tools)
    # Should produce an assistant message with tool_calls
    assistant_msgs = [m for m in out if m["role"] == "assistant"]
    assert assistant_msgs, "Expected assistant message returned"
    am = assistant_msgs[0]
    assert "tool_calls" in am and isinstance(am["tool_calls"], list)
    tool_call = am["tool_calls"][0]
    assert tool_call["function"]["name"] == "sum"
    # arguments should be json string with our params
    assert json.loads(tool_call["function"]["arguments"]) == {"a": 1}
    # content should have had the <function=...> part removed (trim)
    assert "<function=" not in am["content"]


def test_unexpected_role_raises_930(monkeypatch):
    setup_basic_monkeypatch(monkeypatch)
    messages = [{"role": "ghost", "content": "boo"}]
    with pytest.raises(FunctionCallConversionError) as exc:
        fcc.convert_non_fncall_messages_to_fncall_messages(messages, [])
    assert "Unexpected role" in str(exc.value)
