# file: sweagent/run/common.py:24-47
# asked: {"lines": [35, 37, 38, 39, 41, 42, 44, 47], "branches": [[35, 37], [35, 39], [39, 41], [39, 42], [42, 44], [42, 47]]}
# gained: {"lines": [35, 37, 38, 39, 41, 42, 44, 47], "branches": [[35, 37], [35, 39], [39, 41], [39, 42], [42, 44], [42, 47]]}

import pytest
from sweagent.run.common import _shorten_strings


def test_shorten_string_replacement_and_truncation():
    s = "line1\nline2 extra chars"
    # max_length=10 -> keep first 7 chars (10-3) then add '...'
    result = _shorten_strings(s, max_length=10)
    # newline should be replaced with literal backslash-n before truncation
    assert result == "line1\\n..."


def test_shorten_string_small_max_length():
    s = "abc"
    # max_length=3 -> max_length - 3 == 0 -> should return just '...'
    result = _shorten_strings(s, max_length=3)
    assert result == "..."


def test_recursive_list_and_dict_and_else_branch():
    data = {
        "a": ["hello\nworld", 123, ["longstring" * 3]],
        "b": {"inner": "short"},
    }
    # Use max_length=8 so strings are truncated to 5 chars + '...'
    result = _shorten_strings(data, max_length=8)

    # Verify structure preserved and strings truncated as expected
    assert isinstance(result, dict)
    assert "a" in result and "b" in result

    assert isinstance(result["a"], list)
    # first element: "hello\nworld" -> "hello\\nworld" -> first 5 chars "hello" + "..."
    assert result["a"][0] == "hello..."
    # second element is an int and should be returned as-is
    assert result["a"][1] == 123
    # nested list element should be processed recursively
    assert result["a"][2] == ["longs..."]
    # nested dict value should be processed
    assert result["b"] == {"inner": "short..."}


def test_no_inplace_mutation_for_list_input():
    original = ["x\ny"]
    # Make a shallow copy to compare afterward
    original_copy = list(original)
    result = _shorten_strings(original, max_length=10)

    # original should not be modified (no in-place mutation)
    assert original == original_copy
    # result should be a new list with transformed string
    assert result == ["x\\ny..."]


def test_else_branch_with_non_string_non_list_non_dict():
    value = 42
    result = _shorten_strings(value, max_length=10)
    # non-string/list/dict should be returned unchanged
    assert result == 42
    # identity for immutable ints is fine to check equality only
