import pytest

from aider.utils import split_chat_history_markdown


def test_simple_assistant_round_017():
    """
    A single ordinary line should be returned as an assistant message because
    during processing the line is collected into assistant and flushed at the end.
    """
    text = "Hello assistant\n"
    result = split_chat_history_markdown(text)

    # Expect a single assistant message with the original line (including newline)
    assert isinstance(result, list)
    assert result == [{"role": "assistant", "content": "Hello assistant\n"}]


def test_tool_preserved_and_order_round_017():
    """
    This exercises sequences that create assistant, tool, user, assistant messages
    and ensures that when include_tool=True the tool message is preserved and
    ordering/content are as expected.

    Sequence explanation (per line):
    - "First assistant line\n" -> accumulates into assistant
    - "> tool1\n" -> moves assistant into messages, creates a tool entry
    - "#### Head\n" -> flushes tool into messages and puts 'Head\n' into user
    - "User content\n" -> flushes user into messages and accumulates assistant
    Final flush adds the final assistant
    """
    text = (
        "First assistant line\n"
        "> tool1\n"
        "#### Head\n"
        "User content\n"
    )

    result = split_chat_history_markdown(text, include_tool=True)

    # We expect four messages in this order:
    # 1) assistant with 'First assistant line\n'
    # 2) tool with 'tool1\n'
    # 3) user with 'Head\n'
    # 4) assistant with 'User content\n'
    assert [m["role"] for m in result] == ["assistant", "tool", "user", "assistant"]
    assert result[0]["content"] == "First assistant line\n"
    assert result[1]["content"] == "tool1\n"
    assert result[2]["content"] == "Head\n"
    assert result[3]["content"] == "User content\n"


def test_whitespace_user_not_appended_round_017():
    """
    A '#### ' line with only whitespace after it results in a user element that is
    purely whitespace; append_msg should not add an empty/whitespace-only message.
    """
    text = "#### \n"
    result = split_chat_history_markdown(text, include_tool=True)

    # No messages should be produced because the only candidate user content is just a newline
    assert result == []
