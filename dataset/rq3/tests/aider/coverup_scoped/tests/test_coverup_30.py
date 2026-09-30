# file: aider/coders/base_coder.py:1628-1679
# asked: {"lines": [1643, 1647, 1651, 1662, 1663, 1664, 1665, 1666, 1667, 1670, 1671, 1672, 1673, 1674, 1675], "branches": [[1630, 1632], [1642, 1643], [1646, 1647], [1650, 1651], [1661, 1662], [1666, 1667], [1666, 1669], [1669, 1670]]}
# gained: {"lines": [1643, 1647, 1651, 1662, 1663, 1664, 1665, 1666, 1667, 1670, 1671, 1672, 1673, 1674, 1675], "branches": [[1630, 1632], [1642, 1643], [1646, 1647], [1650, 1651], [1661, 1662], [1666, 1667], [1669, 1670]]}

import types
import pytest

from aider.coders.base_coder import Coder
from aider import urls


class DummyIO:
    def __init__(self):
        self.last_tool_error = None
        self.last_offer_url = None

    def tool_error(self, msg: str):
        # capture the message for assertions
        self.last_tool_error = msg

    def offer_url(self, url):
        self.last_offer_url = url


class Msgs:
    def __init__(self, msg):
        self._msg = msg

    def all_messages(self):
        return self._msg


class DummyModel:
    def __init__(self, info, name="dummy", edit_format=None, token_count_fn=None):
        self.info = info
        self.name = name
        self.edit_format = edit_format or []
        # token_count_fn should be a callable that accepts the text and returns int
        self._token_count_fn = token_count_fn or (lambda text: 0)

    def token_count(self, text):
        return self._token_count_fn(text)


def bind_and_call_show_exhausted(dummy):
    # bind the unbound function to the dummy instance and call it
    bound = types.MethodType(Coder.show_exhausted_error, dummy)
    bound()


def test_show_exhausted_error_triggers_input_suggestions_and_handles_no_partial():
    """
    Covers branch where self.partial_response_content is falsy (1630->1632),
    and executes the block that appends input-token reduction suggestions
    (1670-1675). Also checks that fudge-related messages appear.
    """
    io = DummyIO()

    # token_count returns 80 for the messages
    def token_count_fn(text):
        assert text == "MSG"  # ensure called with our messages
        return 80

    main_model = DummyModel(
        info={
            "max_output_tokens": 150,  # large enough that output suggestions won't trigger
            "max_input_tokens": 80,  # equal to input_tokens to trigger >= checks
        },
        name="m1",
        edit_format=["json"],
        token_count_fn=token_count_fn,
    )

    dummy = types.SimpleNamespace()
    dummy.partial_response_content = None  # falsy branch
    dummy.main_model = main_model
    dummy.format_messages = lambda: Msgs("MSG")
    dummy.io = io

    # Call the method
    bind_and_call_show_exhausted(dummy)

    # Assertions
    assert io.last_tool_error is not None, "tool_error should have been called"
    msg = io.last_tool_error

    # Should mention the model and token limit
    assert "Model m1 has hit a token limit!" in msg

    # Input tokens line should show 80 of 80 and include the "possibly exhausted context window!" marker
    assert "Input tokens: ~80 of 80" in msg
    assert "possibly exhausted context window!" in msg

    # Should include the "To reduce input tokens:" section and its items
    assert "To reduce input tokens:" in msg
    assert "- Use /tokens to see token usage." in msg
    assert "- Use /drop to remove unneeded files from the chat session." in msg
    assert "- Use /clear to clear the chat history." in msg
    assert "- Break your code into smaller source files." in msg

    # offer_url should have been called with the token_limits URL
    assert io.last_offer_url == urls.token_limits


def test_show_exhausted_error_triggers_output_suggestions_and_out_err_and_diff_handling():
    """
    Covers branches where partial_response_content is truthy (so output_tokens is computed),
    out_err is set (1642-1643), the output suggestions block runs (1661-1667),
    and the '- Use a stronger model...' line is added when 'diff' not in edit_format.
    """
    io = DummyIO()

    PART = "PART"
    MSG = "MSG"

    def token_count_fn(text):
        # Return different counts depending on whether we're counting the partial response or messages
        if text == PART:
            return 120  # large output to trigger output suggestions (>= max_output_tokens)
        if text == MSG:
            return 10  # small input
        # Defensive fallback
        return 0

    main_model = DummyModel(
        info={
            "max_output_tokens": 100,
            "max_input_tokens": 200,
        },
        name="big-output-model",
        edit_format=["json"],  # does NOT include 'diff', so we expect the stronger-model suggestion
        token_count_fn=token_count_fn,
    )

    dummy = types.SimpleNamespace()
    dummy.partial_response_content = PART  # truthy branch -> output_tokens computed
    dummy.main_model = main_model
    dummy.format_messages = lambda: Msgs(MSG)
    dummy.io = io

    # Call the method
    bind_and_call_show_exhausted(dummy)

    # Assertions
    assert io.last_tool_error is not None, "tool_error should have been called"
    msg = io.last_tool_error

    # Should mention the model and token limit
    assert "Model big-output-model has hit a token limit!" in msg

    # Output tokens line should show 120 of 100 and include the 'possibly exceeded output limit!' marker
    assert "Output tokens: ~120 of 100" in msg
    assert "possibly exceeded output limit!" in msg

    # Should include the "To reduce output tokens:" section and its items
    assert "To reduce output tokens:" in msg
    assert "- Ask for smaller changes in each request." in msg
    assert "- Break your code into smaller source files." in msg

    # Because 'diff' not in edit_format, the stronger-model suggestion should appear
    assert "- Use a stronger model that can return diffs." in msg

    # Since input is small, the input suggestions should NOT be present
    assert "To reduce input tokens:" not in msg

    # offer_url should have been called with the token_limits URL
    assert io.last_offer_url == urls.token_limits
