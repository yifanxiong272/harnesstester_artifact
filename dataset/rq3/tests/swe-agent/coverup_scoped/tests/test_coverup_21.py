# file: sweagent/run/common.py:24-47
# asked: {"lines": [35, 37, 38, 39, 41, 42, 44, 47], "branches": [[35, 37], [35, 39], [39, 41], [39, 42], [42, 44], [42, 47]]}
# gained: {"lines": [35, 37, 38, 39, 41, 42, 44, 47], "branches": [[35, 37], [35, 39], [39, 41], [39, 42], [42, 44], [42, 47]]}

import pytest
from sweagent.run.common import _shorten_strings


def test_shorten_strings_str_and_newline():
    # Test with newline and longer than max_length
    s = "line1\nline2long"
    max_length = 10
    replaced = s.replace("\n", "\\n")
    expected = replaced[: max_length - 3] + "..."
    out = _shorten_strings(s, max_length=max_length)
    assert out == expected
    assert len(out) == max_length

    # Test with short string (function still appends "...")
    s2 = "hi"
    max_length2 = 6
    expected2 = s2.replace("\n", "\\n")[: max_length2 - 3] + "..."
    out2 = _shorten_strings(s2, max_length=max_length2)
    assert out2 == expected2
    # For short strings the result length is original length + 3 (the appended "...")
    assert len(out2) == len(s2.replace("\n", "\\n")) + 3


def test_shorten_strings_list_and_dict_and_nested():
    data = {
        "a": ["hello\nworld", 42, {"b": "x" * 50}],
        "c": None,
    }
    max_length = 20
    out = _shorten_strings(data, max_length=max_length)

    # Ensure top-level is a dict and keys preserved
    assert isinstance(out, dict)
    assert set(out.keys()) == set(data.keys())

    # Check list processing
    assert isinstance(out["a"], list)
    # first element had a newline which should be escaped and then truncated/ellipsized
    replaced_first = "hello\nworld".replace("\n", "\\n")
    expected_first = replaced_first[: max_length - 3] + "..."
    assert out["a"][0] == expected_first

    # integer should be unchanged
    assert out["a"][1] == 42

    # nested dict value should be truncated
    expected_b = ("x" * 50)[: max_length - 3] + "..."
    assert isinstance(out["a"][2], dict)
    assert out["a"][2]["b"] == expected_b

    # None should remain None
    assert out["c"] is None


def test_shorten_strings_else_returns_same_object():
    class Sentinel:
        pass

    sentinel = Sentinel()
    out = _shorten_strings(sentinel, max_length=10)
    # For non-str/list/dict, function should return the same object (identity preserved)
    assert out is sentinel
