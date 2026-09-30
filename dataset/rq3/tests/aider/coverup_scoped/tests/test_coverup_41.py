# file: aider/coders/base_coder.py:1836-1898
# asked: {"lines": [1841, 1844, 1845, 1854, 1855, 1862, 1863, 1867, 1868, 1878, 1879, 1880, 1898], "branches": [[1840, 1841], [1843, 1844], [1850, 1857], [1877, 1878], [1894, 1898]]}
# gained: {"lines": [1841, 1844, 1845, 1854, 1855, 1862, 1863, 1867, 1868, 1878, 1879, 1880, 1898], "branches": [[1840, 1841], [1843, 1844], [1877, 1878], [1894, 1898]]}

import hashlib
import json
import builtins
import pytest

import aider.coders.base_coder as base_coder


class FakeIO:
    def __init__(self):
        self.tool_errors = []
        self.assistant_outputs = []

    def tool_error(self, msg):
        self.tool_errors.append(msg)

    def assistant_output(self, msg, pretty=False):
        self.assistant_outputs.append((msg, pretty))


class FakeMessage:
    def __init__(self, tool_calls=None, content=None, reasoning_content=None, reasoning=None):
        # Only set attributes that are provided to allow AttributeError for missing ones
        if tool_calls is not None:
            self.tool_calls = tool_calls
        if content is not None:
            self.content = content
        if reasoning_content is not None:
            self.reasoning_content = reasoning_content
        if reasoning is not None:
            self.reasoning = reasoning


class FakeToolCall:
    def __init__(self, function):
        self.function = function


class FakeChoice:
    def __init__(self, message, finish_reason=None):
        self.message = message
        if finish_reason is not None:
            self.finish_reason = finish_reason


class FakeCompletion:
    def __init__(self, choices):
        self.choices = choices

    def __str__(self):
        # For printing in verbose mode
        return f"FakeCompletion(choices={len(self.choices)})"


def bind_show_send_output_to(obj):
    """Bind the Coder.show_send_output function to a plain object instance."""
    return base_coder.Coder.show_send_output.__get__(obj, obj.__class__)


def compute_expected_hash(function_call, content):
    resp_hash = dict(function_call=str(function_call), content=content)
    resp_hash = hashlib.sha1(json.dumps(resp_hash, sort_keys=True).encode())
    return resp_hash.hexdigest()


def make_dummy_coder():
    """Create a simple object with the attributes/methods used by show_send_output."""
    class Dummy:
        def __init__(self):
            self.verbose = False
            self.io = FakeIO()
            self.partial_response_function_call = None
            self.partial_response_content = ""
            self.chat_completion_response_hashes = []
            self.reasoning_tag_name = "reason"
            self._stopped = False

        def _stop_waiting_spinner(self):
            self._stopped = True

        def render_incremental_response(self, arg):
            # simple deterministic rendered response
            return "RENDERED"

        def show_pretty(self):
            return True

    return Dummy()


def test_show_send_output_no_choices():
    dummy = make_dummy_coder()
    method = bind_show_send_output_to(dummy)
    completion = FakeCompletion([])

    # Call - should call io.tool_error and return without raising
    method(completion)

    assert dummy._stopped is True, "Spinner should be stopped"
    assert len(dummy.io.tool_errors) == 1
    # tool_error should be called with the string form of completion
    assert str(completion) in dummy.io.tool_errors[0]
    # no hashes should be added
    assert dummy.chat_completion_response_hashes == []


def test_show_send_output_with_tool_call_and_reasoning_content(monkeypatch, capsys):
    dummy = make_dummy_coder()
    # ensure verbose triggers the print(completion) line
    dummy.verbose = True
    method = bind_show_send_output_to(dummy)

    # Prepare completion with a tool call, content and reasoning_content
    func_obj = FakeToolCall(function="the_function_name")
    message = FakeMessage(tool_calls=[func_obj], content="the content", reasoning_content="some reasoning")
    choice = FakeChoice(message=message, finish_reason="stop")
    completion = FakeCompletion([choice])

    # Monkeypatch format_reasoning_content and replace_reasoning_tags to known outputs
    monkeypatch.setattr(base_coder, "format_reasoning_content", lambda rc, name: f"FORMATTED[{name}]:{rc}\n")
    monkeypatch.setattr(base_coder, "replace_reasoning_tags", lambda text, name: text.replace(f"<{name}>", ""))
    # Ensure assistant_output records calls via dummy.io

    method(completion)

    # verbose True should have printed the completion
    captured = capsys.readouterr()
    assert "FakeCompletion" in captured.out

    # partial response function should have been set from tool_calls
    assert dummy.partial_response_function_call == "the_function_name"
    # partial response content should be set
    assert dummy.partial_response_content == "the content"
    # a hash should have been appended and be correct
    expected_hash = compute_expected_hash("the_function_name", "the content")
    assert dummy.chat_completion_response_hashes[-1] == expected_hash
    # assistant_output should have been called once with the formatted reasoning and rendered content
    assert len(dummy.io.assistant_outputs) == 1
    out_msg, pretty = dummy.io.assistant_outputs[0]
    assert out_msg.startswith("FORMATTED[reason]:some reasoning\nRENDERED")
    assert pretty is True


def test_show_send_output_missing_tool_and_content_causes_no_data(monkeypatch):
    dummy = make_dummy_coder()
    method = bind_show_send_output_to(dummy)

    # Message missing tool_calls and content (attributes absent) -> AttributeError on access
    message = FakeMessage()  # nothing set
    choice = FakeChoice(message=message)
    completion = FakeCompletion([choice])

    # Call and expect the special Exception about no data found, after two tool_error calls
    with pytest.raises(Exception) as excinfo:
        method(completion)

    assert "No data found" in str(excinfo.value)
    # Two tool_error calls should have been made for func_err and content_err
    assert len(dummy.io.tool_errors) == 2
    # Both tool_error args should be exceptions (AttributeError instances)
    assert all(isinstance(x, AttributeError) for x in dummy.io.tool_errors)


def test_show_send_output_raises_finish_reason_length(monkeypatch):
    dummy = make_dummy_coder()
    method = bind_show_send_output_to(dummy)

    # Message with content so it goes through assistant_output, but finish_reason == 'length'
    message = FakeMessage(content="short content")
    choice = FakeChoice(message=message, finish_reason="length")
    completion = FakeCompletion([choice])

    # Patch replace/format to pass-through
    monkeypatch.setattr(base_coder, "format_reasoning_content", lambda rc, name: rc)
    monkeypatch.setattr(base_coder, "replace_reasoning_tags", lambda text, name: text)

    with pytest.raises(base_coder.FinishReasonLength):
        method(completion)

    # assistant_output should have been called before the FinishReasonLength was raised
    assert len(dummy.io.assistant_outputs) == 1
    out_msg, pretty = dummy.io.assistant_outputs[0]
    assert "RENDERED" in out_msg or "short content" in out_msg
