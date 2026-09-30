# file: aider/coders/base_coder.py:946-962
# asked: {"lines": [948, 950, 951, 952, 954, 957, 958, 959, 960, 961, 962], "branches": [[950, 951], [950, 954], [959, 960], [959, 962]]}
# gained: {"lines": [948, 950, 951, 952, 954, 957, 958, 959, 960, 961, 962], "branches": [[950, 951], [950, 954], [959, 960], [959, 962]]}

import pytest

from aider.coders.base_coder import Coder


class DummyIO:
    def __init__(self):
        self.warnings = []
        self.errors = []
        self.offered = []

    def tool_warning(self, msg):
        self.warnings.append(msg)

    def tool_error(self, msg):
        self.errors.append(msg)

    def offer_url(self, url):
        self.offered.append(url)


def make_coder_with_io(io):
    # Create Coder instance without running its __init__, since check_and_open_urls
    # only needs .io attribute.
    coder = object.__new__(Coder)
    coder.io = io
    return coder


def _strip_match(m):
    return m.rstrip(".',\"}")


def test_check_and_open_urls_no_friendly():
    io = DummyIO()
    coder = make_coder_with_io(io)

    # Exception text contains duplicate URLs and trailing punctuation that should be stripped.
    exc_text = (
        "Something failed. See http://example.com/foo., for details. "
        "Also check http://example.com/bar'} and repeat http://example.com/foo.,"
    )
    exc = Exception(exc_text)

    urls = coder.check_and_open_urls(exc)

    # The returned urls are the raw regex matches; each offered url should be the stripped form.
    assert len(io.offered) == len(set(io.offered))  # offered should be unique per loop
    expected_offered = {"http://example.com/foo", "http://example.com/bar"}
    assert set(io.offered) == expected_offered

    # For every offered URL, there must be at least one returned raw URL that strips to it.
    returned_set = set(urls)
    for offered in io.offered:
        assert any(_strip_match(r) == offered for r in returned_set)

    # Since no friendly_msg was provided, tool_error should be called with full exception text.
    assert io.errors == [exc_text]
    # No warnings expected in this branch.
    assert io.warnings == []


def test_check_and_open_urls_with_friendly():
    io = DummyIO()
    coder = make_coder_with_io(io)

    # Include URLs with punctuation that should be stripped by offer_url call.
    exc_text = 'Error occurred at "http://example.org/path"} and also at http://example.org/other."'
    exc = RuntimeError(exc_text)
    friendly = "A friendly error occurred. See the links we found."

    urls = coder.check_and_open_urls(exc, friendly_msg=friendly)

    # Offered URLs should be the cleaned versions
    expected_offered = {"http://example.org/path", "http://example.org/other"}
    assert set(io.offered) == expected_offered

    # Ensure returned raw matches correspond to offered after stripping
    returned_set = set(urls)
    for offered in io.offered:
        assert any(_strip_match(r) == offered for r in returned_set)

    # When friendly_msg is provided, tool_warning should be called with the original text,
    # and tool_error should be called with the friendly message.
    assert io.warnings == [exc_text]
    assert io.errors == [friendly]
