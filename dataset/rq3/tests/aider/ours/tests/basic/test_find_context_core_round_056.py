import pytest

from aider.coders.patch_coder import find_context_core


def test_empty_context_round_056():
    # When context is empty, should return the provided start index and fuzz 0
    lines = ["line1", "line2", "line3"]
    context = []
    start = 1
    result = find_context_core(lines, context, start)
    assert result == (1, 0)


def test_exact_match_round_056():
    # Exact match should return the exact index and fuzz 0
    lines = ["a", "b", "c", "d"]
    context = ["b", "c"]
    start = 0
    idx, fuzz = find_context_core(lines, context, start)
    assert (idx, fuzz) == (1, 0)


def test_rstrip_match_round_056():
    # lines have trailing whitespace that prevents exact match but rstrip() makes them match
    lines = ["prefix", "foo ", "bar\t", "suffix"]
    # context items have no trailing whitespace; rstrip match should succeed with fuzz 1
    context = ["foo", "bar"]
    start = 0
    idx, fuzz = find_context_core(lines, context, start)
    assert (idx, fuzz) == (1, 1)


def test_strip_match_round_056():
    # Construct a situation where exact and rstrip matches fail but strip() match succeeds.
    # Context contains a trailing space so norm_context (rstrip) will be stripped of that, but
    # rstrip of the lines will preserve leading spaces causing rstrip comparison to fail.
    # A final strip() comparison will match and return fuzz 100.
    lines = ["  X", "other"]
    context = ["X "]  # trailing space in context
    start = 0
    idx, fuzz = find_context_core(lines, context, start)
    assert (idx, fuzz) == (0, 100)


def test_not_found_round_056():
    # No matching region at or after start should return (-1, 0)
    lines = ["one", "two"]
    context = ["three", "four"]
    start = 0
    assert find_context_core(lines, context, start) == (-1, 0)
