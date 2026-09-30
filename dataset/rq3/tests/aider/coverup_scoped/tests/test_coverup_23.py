# file: aider/coders/patch_coder.py:59-78
# asked: {"lines": [61, 62, 65, 66, 67, 69, 70, 71, 72, 74, 75, 76, 77, 78], "branches": [[61, 62], [61, 65], [65, 66], [65, 69], [66, 65], [66, 67], [70, 71], [70, 74], [71, 70], [71, 72], [75, 76], [75, 78], [76, 75], [76, 77]]}
# gained: {"lines": [61, 62, 65, 66, 67, 69, 70, 71, 72, 74, 75, 76, 77, 78], "branches": [[61, 62], [61, 65], [65, 66], [65, 69], [66, 65], [66, 67], [70, 71], [70, 74], [71, 70], [71, 72], [75, 76], [75, 78], [76, 75], [76, 77]]}

import pytest
from aider.coders.patch_coder import find_context_core

def test_empty_context_returns_start():
    lines = ["one", "two", "three"]
    start = 2
    idx, fuzz = find_context_core(lines, [], start)
    assert idx == start and fuzz == 0

def test_exact_match_found():
    lines = ["a", "b", "c", "d"]
    context = ["b", "c"]
    idx, fuzz = find_context_core(lines, context, 0)
    assert idx == 1
    assert fuzz == 0

def test_rstrip_match_precedes_strip_and_exact():
    # lines contain trailing spaces so exact match fails,
    # but rstrip of lines matches the context (no trailing spaces).
    lines = ["a", "b  ", "c   ", "d"]
    context = ["b", "c"]
    idx, fuzz = find_context_core(lines, context, 0)
    assert idx == 1
    assert fuzz == 1  # rstrip match should produce fuzz level 1

def test_strip_match_when_rstrip_and_exact_fail():
    # context has leading and trailing spaces; lines are the stripped version.
    # exact fails (different whitespace), rstrip fails (because context rstrip keeps leading space),
    # but strip matches and yields fuzz level 100.
    lines = ["b"]
    context = [" b "]
    idx, fuzz = find_context_core(lines, context, 0)
    assert idx == 0
    assert fuzz == 100  # strip match should produce fuzz level 100

def test_no_match_returns_minus_one_zero():
    lines = ["alpha", "beta"]
    context = ["gamma"]
    idx, fuzz = find_context_core(lines, context, 0)
    assert idx == -1 and fuzz == 0
