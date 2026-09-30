import pytest

from sweagent.run.common import _shorten_strings


def test_shorten_string_newline_and_truncate_round_039():
    # Input contains a newline which should be replaced by a literal backslash+n sequence
    # and then truncated to (max_length - 3) characters plus '...'. Using the default max_length=30.
    inp = "1234567890\nABCDEFGHIJKLMNOPQRSTUVWXYZ"
    # After replacing "\n" -> "\\n", taking first 27 chars and adding '...'
    expected = "1234567890\\nABCDEFGHIJKLMNO..."

    out = _shorten_strings(inp)
    assert isinstance(out, str)
    assert out == expected


def test_shorten_list_and_nested_round_039():
    # Lists should be processed element-wise, recursively.
    # Strings are always processed by the string branch: newline replaced and truncated to max_length-3 + '...'.
    data = [
        "hello",
        "LONGSTRINGWITH\nMORESTUFF",
        ["abc\ndefghijklmnopqrstuvwxyz", 123],
    ]

    # Use a smaller max_length to make truncation obvious and deterministic.
    out = _shorten_strings(data, max_length=20)

    # Given max_length=20 -> slice length = 17, then '...'
    assert out[0] == "hello..."  # 'hello' is shorter than slice but function still appends '...'
    assert out[1] == "LONGSTRINGWITH\\nM..."  # newline turns into '\\n' and then truncated
    # nested list: first element is truncated and contains replaced newline; second stays as integer
    assert isinstance(out[2], list)
    assert out[2][0] == "abc\\ndefghijklmno..."
    assert out[2][1] == 123


def test_shorten_dict_and_non_string_round_039():
    # Dict values should be processed recursively; non-string/list/dict types should be returned unchanged.
    data = {
        "k1": "short\ns",
        "k2": {"inner": 42},
        "k3": 987654321987,
    }

    out = _shorten_strings(data, max_length=10)

    # For max_length=10 -> slice length = 7, then '...'
    assert out["k1"] == "short\\n..."
    # nested dict preserved with its integer unchanged
    assert isinstance(out["k2"], dict)
    assert out["k2"]["inner"] == 42
    # numeric types should be returned as-is
    assert out["k3"] == 987654321987
