import pytest

from sweagent.agent.history_processors import _set_content_text


def test_set_content_text_replaces_string_content_round_093():
    entry = {"role": "assistant", "content": "old text"}

    _set_content_text(entry, "new text")

    # When content is a plain string it should be replaced with the provided text
    assert entry["content"] == "new text"


def test_set_content_text_updates_single_list_item_round_093():
    # content as a single-item list of message dicts should have its [0]["text"] replaced
    entry = {"role": "assistant", "content": [{"text": "old", "meta": 1} ]}

    _set_content_text(entry, "updated")

    assert isinstance(entry["content"], list)
    assert len(entry["content"]) == 1
    # the inner dict's "text" key must be updated
    assert entry["content"][0]["text"] == "updated"
    # other keys preserved
    assert entry["content"][0]["meta"] == 1


def test_set_content_text_asserts_on_multiple_items_round_093():
    # If content is a list with length != 1 the function asserts
    entry = {"role": "assistant", "content": [{"text": "a"}, {"text": "b"}]}

    with pytest.raises(AssertionError) as excinfo:
        _set_content_text(entry, "ignored")

    assert "Expected single message in content" in str(excinfo.value)
