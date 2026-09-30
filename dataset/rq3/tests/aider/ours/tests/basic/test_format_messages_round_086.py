import pytest

from aider.utils import format_messages


def test_title_line_round_086():
    # Title present should produce an upper-cased title followed by 50 stars
    out = format_messages([], title="hello")
    assert out == "HELLO " + "*" * 50


def test_content_list_dict_with_url_round_086():
    # A list content with a dict value that contains a 'url' should produce a URL line
    msg = {"role": "assistant", "content": [{"image": {"url": "http://example.com/pic.png"}}]}
    out = format_messages([msg])
    expected = "-------\nASSISTANT Image URL: http://example.com/pic.png"
    assert out == expected


def test_content_list_dict_value_non_url_round_086():
    # A dict value without 'url' should be stringified in the output
    msg = {"role": "assistant", "content": [{"meta": {"a": 1}}]}
    out = format_messages([msg])
    # Expect the Meta key and the dict value string representation
    assert out.startswith("-------\nASSISTANT Meta: ")
    assert "{'a': 1}" in out


def test_content_list_non_dict_item_round_086():
    # Non-dict list items should be appended as a simple role + item line
    msg = {"role": "assistant", "content": ["a simple caption"]}
    out = format_messages([msg])
    expected = "-------\nASSISTANT a simple caption"
    assert out == expected


def test_function_call_with_no_content_round_086():
    # If content is None but a function_call is present, only the Function Call line should be appended
    msg = {"role": "system", "content": None, "function_call": "do_it()"}
    out = format_messages([msg])
    expected = "-------\nSYSTEM Function Call: do_it()"
    assert out == expected
