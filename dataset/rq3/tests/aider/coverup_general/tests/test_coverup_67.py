# file: aider/coders/udiff_coder.py:261-279
# asked: {"lines": [262, 264, 265, 267, 268, 271, 272, 274, 275, 276, 277, 279], "branches": [[264, 265], [264, 267], [271, 272], [271, 274]]}
# gained: {"lines": [262, 264, 265, 267, 268, 271, 272, 274, 275, 276, 277, 279], "branches": [[264, 265], [264, 267], [271, 272], [271, 274]]}

import pytest

from aider.coders import udiff_coder
from aider.coders.udiff_coder import directly_apply_hunk
from aider.coders.search_replace import SearchTextNotUnique


def test_before_empty_returns_none():
    # Hunk that only has an addition -> before should be empty, so function returns None
    hunk = ["+added_line"]
    result = directly_apply_hunk("some content", hunk)
    assert result is None


def test_small_before_repeated_returns_none():
    # before is 'foo' (length < 10) and appears more than once in content -> should return None
    hunk = [" foo"]
    content = "start_foo_middle_foo_end"
    # Sanity check that before is indeed 'foo' and appears >1
    before, _ = udiff_coder.hunk_to_before_after(hunk)
    assert before == "foo"
    assert content.count(before) > 1

    result = directly_apply_hunk(content, hunk)
    assert result is None


def test_flexi_raises_search_text_not_unique_results_in_none(monkeypatch):
    # Create a before that is long enough (>=10) so we don't trigger the small-before early return,
    # and appears only once in content so that we don't return early for repeated context.
    long_before = "X" * 12
    hunk = [f" {long_before}"]
    content = f"prefix{long_before}suffix"
    assert content.count(long_before) == 1

    # Monkeypatch flexi_just_search_and_replace to raise SearchTextNotUnique
    called = {"flag": False}

    def fake_flexi(texts):
        called["flag"] = True
        raise SearchTextNotUnique("not unique")

    monkeypatch.setattr(udiff_coder, "flexi_just_search_and_replace", fake_flexi)

    result = directly_apply_hunk(content, hunk)
    assert called["flag"] is True
    # When the underlying flexi function raises SearchTextNotUnique, directly_apply_hunk should return None
    assert result is None


def test_flexi_returns_new_content(monkeypatch):
    # Create a before that is long enough (>=10) and appears only once.
    long_before = "ABCDEFGHIJK"  # length 11
    hunk = [f" {long_before}", f"+replacement"]
    content = f"start{long_before}end"
    assert content.count(long_before) == 1

    # Monkeypatch flexi_just_search_and_replace to return a new content
    def fake_flexi(texts):
        # texts is [before, after, content] as passed by directly_apply_hunk
        assert texts[0] == long_before
        # Return a transformed content string
        return texts[2].replace(texts[0], "REPLACED")

    monkeypatch.setattr(udiff_coder, "flexi_just_search_and_replace", fake_flexi)

    result = directly_apply_hunk(content, hunk)
    assert result == content.replace(long_before, "REPLACED")
