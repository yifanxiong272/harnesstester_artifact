import pytest
from gpt_researcher.skills import deep_research


def _make_fake_count(map_counts):
    """Return a deterministic count_words replacement using the provided mapping.
    Falls back to splitting on whitespace if a string isn't in the mapping.
    """
    def _fake(s):
        return map_counts.get(s, len(s.split()))
    return _fake


def test_trim_basic_round_110(monkeypatch):
    # Setup deterministic counts for three items.
    mapping = {
        "one two": 2,
        "three four five": 3,
        "six": 1,
    }
    monkeypatch.setattr(deep_research, "count_words", _make_fake_count(mapping))

    context = ["one two", "three four five", "six"]
    # Processed in reverse: "six" (1) + "three four five" (3) = 4 <= 5, but adding "one two" (2) would exceed
    result = deep_research.trim_context_to_word_limit(context, max_words=5)
    assert result == ["three four five", "six"], "Should preserve most recent items without exceeding max"


def test_trim_boundary_equal_round_110(monkeypatch):
    # Ensure equality to max_words is allowed
    mapping = {"a": 3, "b": 2}
    monkeypatch.setattr(deep_research, "count_words", _make_fake_count(mapping))

    context = ["a", "b"]
    # reversed: "b" (2) then "a" (3) -> total becomes exactly 5
    result = deep_research.trim_context_to_word_limit(context, max_words=5)
    assert result == ["a", "b"]


def test_trim_break_on_large_item_round_110(monkeypatch):
    # Large item will be rejected and cause break after a small recent item is accepted
    mapping = {"large": 10, "small": 1}
    monkeypatch.setattr(deep_research, "count_words", _make_fake_count(mapping))

    context = ["large", "small"]
    # reversed: "small" accepted, then "large" would exceed -> break
    result = deep_research.trim_context_to_word_limit(context, max_words=5)
    assert result == ["small"]


def test_trim_empty_and_zero_max_round_110(monkeypatch):
    # Empty context should return empty list (loop not entered)
    monkeypatch.setattr(deep_research, "count_words", _make_fake_count({}))
    assert deep_research.trim_context_to_word_limit([], max_words=10) == []

    # With max_words 0, any positive-sized item should be skipped and break immediately
    mapping = {"x": 1}
    monkeypatch.setattr(deep_research, "count_words", _make_fake_count(mapping))
    assert deep_research.trim_context_to_word_limit(["x"], max_words=0) == []
