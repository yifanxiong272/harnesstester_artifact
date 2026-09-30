# file: sweagent/utils/serialization.py:25-33
# asked: {"lines": [26, 27, 28, 29, 30, 31, 32, 33], "branches": []}
# gained: {"lines": [26, 27, 28, 29, 30, 31, 32, 33], "branches": []}

import re
from sweagent.utils.serialization import _yaml_serialization_with_linebreaks


def test_yaml_serialization_with_linebreaks_dict_multiline():
    data = {"greeting": "hello\nworld", "single": "one line"}
    out = _yaml_serialization_with_linebreaks(data)

    # output must be a non-empty string
    assert isinstance(out, str)
    assert out

    # The multiline string should be represented with YAML block scalar indicator (|).
    assert re.search(r"^greeting:\s*\|", out, flags=re.MULTILINE), out

    # The content lines in YAML are indented; match 'hello' then newline then optional spaces then 'world'.
    assert re.search(r"hello\n\s*world", out), out

    # No raw CR characters should be present in the YAML output
    assert "\r" not in out

    # The single-line value should still be present on the same line
    assert re.search(r"^single:\s*one line", out, flags=re.MULTILINE), out


def test_yaml_serialization_with_linebreaks_list_and_crlf_normalization_behavior():
    data = {
        "items": [
            "line1\r\nline2",  # CRLF should be normalized to LF and become a literal block
            {"nested": "a\rb"}  # CR only; note: conversion only triggers when '\n' present
        ],
        "normal": "no newlines here"
    }
    out = _yaml_serialization_with_linebreaks(data)

    # must be a string and non-empty
    assert isinstance(out, str)
    assert out

    # Only the first list item contains a newline and should become a block scalar.
    # The second item contains only '\r' and should NOT be converted to a block scalar by the implementation.
    pipe_count = out.count("|")
    assert pipe_count == 1, f"expected exactly one '|' block scalar indicator in YAML output; got: {pipe_count}\n{out}"

    # Raw CR characters should not be present (ruamel escapes them); ensure no actual '\r' byte
    assert "\r" not in out

    # The escaped CR sequence should appear for the nested value (it will be represented as '\r' in the YAML text)
    assert "\\r" in out, f"expected escaped CR sequence '\\\\r' in output; got:\n{out}"

    # Normalized contents for the first item should appear (account for YAML indentation)
    assert re.search(r"line1\n\s*line2", out), out

    # The normal single-line entry should remain inline
    assert re.search(r"^normal:\s*no newlines here", out, flags=re.MULTILINE), out
