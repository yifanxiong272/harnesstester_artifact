import pytest

from aider.utils import split_chat_history_markdown


def test_simple_assistant_round_016():
    text = "Hello\n"
    msgs = split_chat_history_markdown(text)
    # single assistant message with exact content preserved
    assert msgs == [{"role": "assistant", "content": "Hello\n"}]


def test_tool_then_assistant_include_tool_round_016():
    # a tool line ("> ") followed by a normal line: the tool entry should be
    # flushed into messages when the next non-tool line is encountered
    text = "> tool action\nHello\n"
    msgs = split_chat_history_markdown(text, include_tool=True)
    assert msgs == [
        {"role": "tool", "content": "tool action\n"},
        {"role": "assistant", "content": "Hello\n"},
    ]


def test_header_and_tool_filtering_round_016():
    # mix of skipped heading, a tool-prefixed line, a #### header (which pushes
    # a user content), then payload lines. When include_tool is False, tool
    # messages should be filtered out.
    text = "# Title\n> tool1\n#### run\npayload\n\n"
    msgs = split_chat_history_markdown(text, include_tool=False)
    # tool message should be removed by filtering; remaining messages in order
    # are the user message from the #### header and the assistant payload
    assert msgs == [
        {"role": "user", "content": "run\n"},
        {"role": "assistant", "content": "payload\n\n"},
    ]


def test_whitespace_only_line_round_016():
    # a single blank line should not produce any messages because append_msg
    # skips content that is only whitespace
    text = "\n"
    msgs = split_chat_history_markdown(text)
    assert msgs == []
