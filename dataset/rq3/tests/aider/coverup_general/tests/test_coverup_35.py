# file: aider/coders/patch_coder.py:59-78
# asked: {"lines": [61, 62, 65, 66, 67, 69, 70, 71, 72, 74, 75, 76, 77, 78], "branches": [[61, 62], [61, 65], [65, 66], [65, 69], [66, 65], [66, 67], [70, 71], [70, 74], [71, 70], [71, 72], [75, 76], [75, 78], [76, 75], [76, 77]]}
# gained: {"lines": [61, 62, 65, 66, 67, 69, 70, 71, 72, 74, 75, 76, 77, 78], "branches": [[61, 62], [61, 65], [65, 66], [65, 69], [66, 65], [66, 67], [70, 71], [70, 74], [71, 70], [71, 72], [75, 76], [75, 78], [76, 75], [76, 77]]}

import pytest
from aider.coders.patch_coder import find_context_core

def test_empty_context_returns_start_and_zero():
    lines = ["one", "two", "three"]
    # empty context should return the provided start and fuzz 0
    assert find_context_core(lines, [], 2) == (2, 0)
    assert find_context_core(lines, [], 0) == (0, 0)

def test_exact_match_found_returns_index_and_zero():
    lines = ["alpha", "beta", "gamma", "delta"]
    context = ["beta", "gamma"]
    # exact match at index 1
    assert find_context_core(lines, context, 0) == (1, 0)
    # with a later start it should not find before start
    assert find_context_core(lines, context, 2) == (-1, 0)

def test_rstrip_match_returns_fuzz_1_when_only_trailing_spaces_in_context():
    # context has trailing spaces that lines do not; exact match fails,
    # but rstrip matching should succeed and return fuzz level 1
    lines = ["first", "second", "third"]
    context = ["first ", "second "]  # trailing spaces in context
    assert find_context_core(lines, context, 0) == (0, 1)

def test_strip_match_returns_fuzz_100_when_only_leading_spaces_in_context():
    # context has leading spaces that rstrip won't remove but strip will;
    # ensures rstrip branch fails and strip branch returns fuzz level 100
    lines = ["one", "two", "three"]
    context = [" one", "two"]  # leading space on first context element
    assert find_context_core(lines, context, 0) == (0, 100)

def test_not_found_returns_minus_one_zero():
    lines = ["a", "b", "c"]
    context = ["x", "y"]
    assert find_context_core(lines, context, 0) == (-1, 0)
