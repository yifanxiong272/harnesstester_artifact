# file: aider/coders/base_coder.py:946-962
# asked: {"lines": [948, 950, 951, 952, 954, 957, 958, 959, 960, 961, 962], "branches": [[950, 951], [950, 954], [959, 960], [959, 962]]}
# gained: {"lines": [948, 950, 951, 952, 954, 957, 958, 959, 960, 961, 962], "branches": [[950, 951], [950, 954], [959, 960], [959, 962]]}

import re
import pytest

from aider.coders.base_coder import Coder


class FakeIO:
    def __init__(self):
        self.tool_warning_calls = []
        self.tool_error_calls = []
        self.offered = []

    def tool_warning(self, msg):
        self.tool_warning_calls.append(msg)

    def tool_error(self, msg):
        self.tool_error_calls.append(msg)

    def offer_url(self, url):
        self.offered.append(url)


def _expected_matches(text):
    url_pattern = re.compile(r'(https?://[^\s/$.?#].[^\s"]*)')
    return list(set(url_pattern.findall(text)))


def _strip_trailing(chars_list):
    return [u.rstrip(".',\"}") for u in chars_list]


def make_coder_with_io(fake_io):
    coder = Coder.__new__(Coder)
    coder.io = fake_io
    return coder


def test_check_and_open_urls_with_friendly_msg():
    fake_io = FakeIO()
    coder = make_coder_with_io(fake_io)

    # Text includes duplicate URL and trailing punctuation/braces to exercise rstrip
    text = (
        "Something went wrong at https://example.com/path.'} and again "
        "https://example.com/path.'} and also check https://other.com/endpoint."
    )
    exc = Exception(text)

    returned = coder.check_and_open_urls(exc, friendly_msg="A friendly message")

    expected_raw = _expected_matches(text)
    expected_offered = set(_strip_trailing(expected_raw))

    # Returned should contain the unique raw matches (order not guaranteed)
    assert set(returned) == set(expected_raw)

    # tool_warning should have been called with the full original text
    assert fake_io.tool_warning_calls == [text]

    # tool_error should have been called with the friendly message (not the raw text)
    assert fake_io.tool_error_calls == ["A friendly message"]

    # offer_url should have been called for each unique URL, with trailing punctuation stripped
    assert set(fake_io.offered) == expected_offered


def test_check_and_open_urls_without_friendly_msg():
    fake_io = FakeIO()
    coder = make_coder_with_io(fake_io)

    text = "No friendly msg, see https://one.test/path, and duplicate https://one.test/path,"
    exc = Exception(text)

    returned = coder.check_and_open_urls(exc, friendly_msg=None)

    expected_raw = _expected_matches(text)
    expected_offered = set(_strip_trailing(expected_raw))

    # When no friendly_msg provided, tool_warning should not be called
    assert fake_io.tool_warning_calls == []

    # tool_error should be called with the exception text
    assert fake_io.tool_error_calls == [text]

    # offer_url called for unique urls with stripped trailing punctuation
    assert set(fake_io.offered) == expected_offered

    # returned list matches the regex-based extraction
    assert set(returned) == set(expected_raw)
