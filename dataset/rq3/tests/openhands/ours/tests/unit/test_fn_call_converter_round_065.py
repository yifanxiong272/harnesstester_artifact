import copy
import pytest

import openhands.llm.fn_call_converter as fc
from openhands.core.exceptions import (
    FunctionCallConversionError,
    FunctionCallValidationError,
)


def test_user_unexpected_content_type_raises_round_065():
    """A user message with a non-str/non-list content should raise FunctionCallConversionError.

    This targets the branch where the first user message's content type is unexpected
    and triggers the explicit conversion error (lines ~788-790 in the segment).
    """
    messages = [
        {"role": "user", "content": 12345},  # unexpected type (int)
    ]

    with pytest.raises(FunctionCallConversionError) as exc:
        fc.convert_non_fncall_messages_to_fncall_messages(messages, tools=[])

    assert "Unexpected content type" in str(exc.value)


def test_assistant_fn_match_exists_but_not_in_last_index_raises_round_065(monkeypatch):
    """If a function-like pattern appears in a non-last text item, it should raise.

    We patch the module's re.search so that it reports a match for items containing
    a sentinel token in their text. We craft a content list where the FIRST item
    (a text item) contains that sentinel and the LAST item is not of type 'text'.
    This should set fn_match_exists True but fn_match None and trigger the
    FunctionCallConversionError at the corresponding branch (lines ~861-869).
    """

    # Make fc.re.search return a match object when the string contains 'FNHIT'
    class _FakeMatch:
        def __init__(self, name="fake", body=""):
            self._name = name
            self._body = body

        def group(self, idx):
            # emulate groups used by the function: group(1)=name, group(2)=body
            return self._name if idx == 1 else self._body

    def fake_search(pattern, string, flags=0):
        if isinstance(string, str) and "FNHIT" in string:
            return _FakeMatch(name="the_fn", body="(arg=1)")
        return None

    monkeypatch.setattr(fc.re, "search", fake_search)

    content = [
        {"type": "text", "text": "some preface FNHIT <function=the_fn()>"},
        {"type": "tool", "payload": "not-text"},  # last item is not 'text'
    ]
    messages = [{"role": "assistant", "content": content}]

    with pytest.raises(FunctionCallConversionError) as exc:
        fc.convert_non_fncall_messages_to_fncall_messages(messages, tools=[])

    # The raised error should complain about expecting the function call in the last index
    assert "Expecting function call in the LAST index" in str(exc.value)


def test_assistant_fn_not_found_raises_round_065(monkeypatch):
    """When a function call is detected but the function isn't present in tools,
    a FunctionCallValidationError should be raised.

    We patch fc.re.search so the assistant content yields a valid fn_match and then
    pass an empty tools list to ensure no matching tool is found.
    This exercises the branch that raises FunctionCallValidationError (lines ~888-891).
    """

    class _FakeMatch2:
        def __init__(self, name="missing_fn", body="(a=1)"):
            self._name = name
            self._body = body

        def group(self, idx):
            return self._name if idx == 1 else self._body

    def fake_search_match_any(pattern, string, flags=0):
        # Always return a match so fn_match becomes truthy and group(1) yields the function name
        return _FakeMatch2()

    monkeypatch.setattr(fc.re, "search", fake_search_match_any)

    # content is a simple string (the actual text is irrelevant due to our patch)
    messages = [{"role": "assistant", "content": "irrelevant but triggers fn_match"}]

    # Empty tools ensures no matching tool exists
    with pytest.raises(FunctionCallValidationError) as exc:
        fc.convert_non_fncall_messages_to_fncall_messages(messages, tools=[])

    assert "Function 'missing_fn' not found" in str(exc.value)


def test_system_content_list_suffix_removal_round_065():
    """System message with content as list should have the system suffix removed

    This constructs the same suffix the function builds internally and ensures the
    last text item gets truncated at that suffix (lines ~754-759 and 752-753).
    If the module doesn't expose the expected template, the test will be skipped
    to avoid brittle dependency on implementation details.
    """
    # Ensure the auxiliary utilities exist; otherwise skip
    template = getattr(fc, "SYSTEM_PROMPT_SUFFIX_TEMPLATE", None)
    convert_fn = getattr(fc, "convert_tools_to_description", None)
    if template is None or convert_fn is None:
        pytest.skip("Module does not expose SYSTEM_PROMPT_SUFFIX_TEMPLATE or convert_tools_to_description")

    tools = []
    formatted_tools = convert_fn(tools)
    system_prompt_suffix = template.format(description=formatted_tools)

    original_text = "important system text"
    content_list = [{"type": "text", "text": original_text + system_prompt_suffix}]
    messages = [{"role": "system", "content": content_list}]

    out = fc.convert_non_fncall_messages_to_fncall_messages(messages, tools=tools)
    # Expect one message returned and its content to be a list with truncated last element
    assert out and out[0]["role"] == "system"
    returned_content = out[0]["content"]
    assert isinstance(returned_content, list)
    # Last text should be the original_text only (suffix removed)
    assert returned_content[-1]["text"] == original_text
