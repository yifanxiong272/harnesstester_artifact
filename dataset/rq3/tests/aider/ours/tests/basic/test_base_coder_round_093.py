import json
import hashlib
import pytest

from aider.coders import base_coder
from aider.coders.base_coder import Coder, FinishReasonLength


class DummyIO:
    def __init__(self):
        self.tool_errors = []
        self.assistant_outputs = []

    def tool_error(self, msg):
        # record the string representation for deterministic assertions
        self.tool_errors.append(str(msg))

    def assistant_output(self, msg, pretty=None):
        # store tuple of (msg, pretty) for assertions
        self.assistant_outputs.append((msg, pretty))


class SimpleMessage:
    def __init__(self, content_present=True, content_value="", tool_calls_present=True, tool_calls=None, reasoning_content=None, reasoning=None):
        # conditionally set attributes to force AttributeError if not present
        if content_present:
            self.content = content_value
        if tool_calls_present:
            # if not provided, default to empty list
            self.tool_calls = [] if tool_calls is None else tool_calls
        if reasoning_content is not None:
            self.reasoning_content = reasoning_content
        if reasoning is not None:
            self.reasoning = reasoning


class SimpleChoice:
    def __init__(self, message, finish_reason=None):
        self.message = message
        if finish_reason is not None:
            self.finish_reason = finish_reason


class SimpleCompletion:
    def __init__(self, choices):
        self.choices = choices

    def __str__(self):
        # deterministic string for print assertions
        return f"SimpleCompletion(choices={len(self.choices)})"


def make_coder_instance():
    # Create a Coder instance without running its heavy __init__
    coder = Coder.__new__(Coder)
    coder.verbose = False
    coder.io = DummyIO()
    coder.partial_response_function_call = None
    coder.partial_response_content = None
    coder.chat_completion_response_hashes = []
    coder.reasoning_tag_name = "REASON"
    # deterministic no-op spinner
    coder._stop_waiting_spinner = lambda: None
    # deterministic incremental renderer
    coder.render_incremental_response = lambda final: "<rendered>"
    coder.show_pretty = lambda: True
    return coder


def test_no_choices_triggers_tool_error_and_return_round_093():
    coder = make_coder_instance()
    # completion with empty choices should invoke tool_error(str(completion)) and return early
    completion = SimpleCompletion(choices=[])

    # Call the method under test
    coder.show_send_output(completion)

    # assert io.tool_error was called exactly once with string of completion
    assert coder.io.tool_errors == [str(completion)]
    # ensure no hashes were appended
    assert coder.chat_completion_response_hashes == []


def test_no_data_in_response_raises_round_093():
    coder = make_coder_instance()
    # message lacks both tool_calls and content --> both attribute accesses raise AttributeError
    message = SimpleMessage(content_present=False, tool_calls_present=False)
    choice = SimpleChoice(message=message)
    completion = SimpleCompletion(choices=[choice])

    # ensure initial partials are None to match branch expectations
    assert coder.partial_response_function_call is None
    assert coder.partial_response_content is None

    with pytest.raises(Exception) as excinfo:
        coder.show_send_output(completion)

    # The code raises a generic Exception with this message when both errors present
    assert "No data found in LLM response!" in str(excinfo.value)

    # io.tool_error should have been called twice (once for function error, once for content error)
    assert len(coder.io.tool_errors) == 2
    # both recorded tool_errors should be string representations of AttributeError objects
    assert all(isinstance(msg, str) for msg in coder.io.tool_errors)


def test_verbose_print_and_finish_length_round_093(capsys):
    coder = make_coder_instance()
    coder.verbose = True

    # message has content; tool_calls exists (empty list) so no AttributeError for tool access
    message = SimpleMessage(content_present=True, content_value="hello world", tool_calls_present=True, tool_calls=[])
    # create choice with finish_reason == 'length' to exercise FinishReasonLength branch
    choice = SimpleChoice(message=message, finish_reason="length")
    completion = SimpleCompletion(choices=[choice])

    # Call and expect FinishReasonLength to be raised after assistant_output
    with pytest.raises(FinishReasonLength):
        coder.show_send_output(completion)

    # print(completion) should have happened due to verbose True; capture stdout
    captured = capsys.readouterr()
    assert str(completion) in captured.out

    # assistant_output should have been called once
    assert len(coder.io.assistant_outputs) == 1
    # and a hash should have been appended to chat_completion_response_hashes
    assert len(coder.chat_completion_response_hashes) == 1
    # hash should be a 40-character SHA1 hex string
    h = coder.chat_completion_response_hashes[0]
    assert isinstance(h, str) and len(h) == 40


def test_reasoning_content_formats_and_assistant_output_round_093(monkeypatch):
    coder = make_coder_instance()

    # Provide reasoning_content so formatting branch is used
    message = SimpleMessage(content_present=True, content_value="answer", tool_calls_present=True, tool_calls=[], reasoning_content="some reasoning")
    choice = SimpleChoice(message=message)
    completion = SimpleCompletion(choices=[choice])

    # Patch the formatting functions where base_coder resolves them
    monkeypatch.setattr(base_coder, "format_reasoning_content", lambda rc, tag: f"FORMATTED({rc})")
    monkeypatch.setattr(base_coder, "replace_reasoning_tags", lambda resp, tag: resp + "::replaced")

    # Run
    coder.show_send_output(completion)

    # assistant_output should have been called once
    assert len(coder.io.assistant_outputs) == 1
    rendered_msg, pretty = coder.io.assistant_outputs[0]

    # formatting should prepend formatted reasoning to rendered response and then tags replaced
    assert rendered_msg.startswith("FORMATTED(some reasoning)")
    assert rendered_msg.endswith("::replaced")
    assert pretty is True

    # ensure a hash was appended to chat_completion_response_hashes
    assert len(coder.chat_completion_response_hashes) == 1
