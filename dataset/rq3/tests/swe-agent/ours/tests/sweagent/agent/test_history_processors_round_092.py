import pytest

from sweagent.agent.history_processors import _get_content_text


def test_get_content_text_str_round_092():
    """When content is a plain string, it should be returned as-is."""
    entry = {"content": "plain text content"}
    result = _get_content_text(entry)
    assert result == "plain text content"


def test_get_content_text_single_message_round_092():
    """When content is a single-item list of message dicts, return the message['text']."""
    entry = {"content": [{"text": "message text"}]}
    result = _get_content_text(entry)
    assert result == "message text"


def test_get_content_text_multiple_messages_asserts_round_092():
    """When content is a list with length != 1, the function must assert with the expected message."""
    entry = {"content": [{"text": "first"}, {"text": "second"}]}
    with pytest.raises(AssertionError, match="Expected single message in content"):
        _get_content_text(entry)
