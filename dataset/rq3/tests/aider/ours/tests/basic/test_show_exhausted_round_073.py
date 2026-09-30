import types
import importlib

import aider.coders.base_coder as base_coder


class FakeIO:
    def __init__(self):
        self.last_tool_error = None
        self.last_offered_url = None

    def tool_error(self, msg):
        # capture the emitted error message for assertions
        self.last_tool_error = msg

    def offer_url(self, url):
        # capture offered URL
        self.last_offered_url = url


class FakeMessages:
    def __init__(self, text_or_count):
        # Accept either a string or an integer count to create predictable messages
        if isinstance(text_or_count, int):
            # produce that many 'w' tokens
            self._text = "w " * text_or_count
        else:
            self._text = str(text_or_count)

    def all_messages(self):
        return self._text


class FakeModel:
    def __init__(self, name, info, edit_format):
        self.name = name
        self.info = info
        self.edit_format = edit_format

    def token_count(self, content):
        # Deterministic token counting: count whitespace-separated words
        if isinstance(content, (list, tuple)):
            s = " ".join(map(str, content))
        else:
            s = str(content)
        # split on whitespace to count tokens
        return len([p for p in s.split() if p])


def _make_self(partial_response_words, input_words, model_info, edit_format):
    io = FakeIO()
    model = FakeModel(name="fake-model", info=model_info, edit_format=edit_format)
    self_obj = types.SimpleNamespace()
    # partial_response_content should be truthy to trigger output token counting when needed
    self_obj.partial_response_content = None if partial_response_words is None else ("w " * partial_response_words).strip()
    self_obj.main_model = model
    # format_messages() must return an object with all_messages()
    self_obj.format_messages = lambda: FakeMessages(input_words)
    self_obj.io = io
    return self_obj


def test_show_exhausted_output_and_diff_suggestion_round_073():
    """
    Cover branch where partial_response_content exists and triggers:
    - out_err (output_tokens >= max_output_tokens * fudge)
    - output section when output_tokens >= max_output_tokens
    - branch where 'diff' not in edit_format so the diff-suggestion line is appended
    Also assert the offer_url is called with the patched token_limits URL.
    """
    # Patch the token limits URL to a deterministic value
    base_coder.urls.token_limits = "http://test-token-limits"

    # Set up model info so that max_output_tokens == 100 and max_input_tokens very large
    model_info = {"max_output_tokens": 100, "max_input_tokens": 10000}

    # Provide 100 output tokens so output_tokens >= max_output_tokens and >= 0.7 * max_output_tokens
    self_obj = _make_self(partial_response_words=100, input_words=2, model_info=model_info, edit_format=["not-diff"]) 

    # Call the function under test
    base_coder.Coder.show_exhausted_error(self_obj)

    emitted = self_obj.io.last_tool_error
    assert emitted is not None, "Expected a tool_error message to have been emitted"
    # out_err message should be present
    assert "possibly exceeded output limit!" in emitted
    # Because output_tokens >= max_output_tokens, the section 'To reduce output tokens:' should appear
    assert "To reduce output tokens:" in emitted
    # Since edit_format does not contain 'diff', the stronger-model suggestion should be present
    assert "Use a stronger model that can return diffs" in emitted
    # The URL offer should have been called with the patched token limits URL
    assert self_obj.io.last_offered_url == "http://test-token-limits"


def test_show_exhausted_input_and_total_suggestions_with_diff_present_round_073():
    """
    Cover branch where input_tokens >= max_input_tokens * fudge and total_tokens triggers tot_err,
    and input_tokens >= max_input_tokens triggers the 'To reduce input tokens' block.
    Also ensure that when 'diff' is present in edit_format the diff-suggestion is not appended.
    """
    base_coder.urls.token_limits = "http://test-token-limits-2"

    # Use modest max_output_tokens but max_input_tokens set to 100 so we can cross it
    model_info = {"max_output_tokens": 1000, "max_input_tokens": 100}

    # No partial response -> output_tokens == 0
    # Provide input_words == 100 so input_tokens == max_input_tokens, which should trigger the
    # input suggestions (input_tokens >= max_input_tokens) and also tot_err (total_tokens >= max_input_tokens)
    self_obj = _make_self(partial_response_words=None, input_words=100, model_info=model_info, edit_format=["diff"])

    base_coder.Coder.show_exhausted_error(self_obj)

    emitted = self_obj.io.last_tool_error
    assert emitted is not None
    # inp_err should appear in the formatted Input tokens line
    assert "possibly exhausted context window!" in emitted
    # The 'To reduce input tokens:' advice block should be present
    assert "To reduce input tokens:" in emitted
    assert "- Use /tokens to see token usage." in emitted
    # Because edit_format contains 'diff', the stronger-model diff suggestion should NOT be present
    assert "Use a stronger model that can return diffs" not in emitted
    # Confirm offer_url was called with the patched value
    assert self_obj.io.last_offered_url == "http://test-token-limits-2"
