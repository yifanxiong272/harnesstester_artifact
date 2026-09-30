# file: sweagent/agent/history_processors.py:23-27
# asked: {"lines": [26, 27], "branches": [[24, 26]]}
# gained: {"lines": [26, 27], "branches": [[24, 26]]}

import pytest

from sweagent.agent.history_processors import _get_content_text


def test_get_content_text_with_string_content():
    entry = {"content": "simple string content"}
    result = _get_content_text(entry)
    assert result == "simple string content"


def test_get_content_text_with_single_message_list():
    entry = {"content": [{"text": "message in list"}]}
    result = _get_content_text(entry)
    assert result == "message in list"


def test_get_content_text_with_wrong_length_list_raises_assertion():
    entry = {"content": [{"text": "one"}, {"text": "two"}]}
    with pytest.raises(AssertionError) as excinfo:
        _get_content_text(entry)
    assert "Expected single message in content" in str(excinfo.value)
