# file: sweagent/utils/serialization.py:9-22
# asked: {"lines": [13, 14, 15, 16, 17, 18, 19, 20, 21, 22], "branches": [[14, 15], [14, 17], [15, 16], [15, 22], [17, 18], [17, 20], [18, 19], [18, 22], [20, 21], [20, 22]]}
# gained: {"lines": [13, 14, 15, 16, 17, 18, 19, 20, 21, 22], "branches": [[14, 15], [14, 17], [15, 16], [15, 22], [17, 18], [17, 20], [18, 19], [18, 22], [20, 21], [20, 22]]}

import copy
import pytest
from ruamel.yaml.scalarstring import LiteralScalarString as LSS

from sweagent.utils.serialization import _convert_to_yaml_literal_string


def test_multiline_conversion_and_original_unchanged():
    original = {
        "a": "single line",
        "b": "multi\nline",
        "c": ["x", "y\nz", {"d": "p\r\nq"}],
    }

    # Keep a deep copy to compare later that original is not modified
    original_copy = copy.deepcopy(original)

    result = _convert_to_yaml_literal_string(original)

    # Original must be unchanged
    assert original == original_copy
    # Original types remain plain str
    assert isinstance(original["b"], str) and not isinstance(original["b"], LSS)
    assert original["c"][2]["d"] == "p\r\nq"

    # Result should have converted multiline strings to LSS, with normalized newlines
    assert isinstance(result, dict)
    assert isinstance(result["a"], str) and not isinstance(result["a"], LSS)
    assert isinstance(result["b"], LSS)
    assert str(result["b"]) == "multi\nline"

    # Nested list item converted
    assert isinstance(result["c"], list)
    assert isinstance(result["c"][1], LSS)
    assert str(result["c"][1]) == "y\nz"

    # Deeply nested dict value converted and normalized CRLF to LF
    assert isinstance(result["c"][2]["d"], LSS)
    assert str(result["c"][2]["d"]) == "p\nq"

    # Modifying the returned structure should not affect the original
    result["a"] = "modified"
    result["c"][2]["d"] = LSS("new\nvalue")
    assert original["a"] == "single line"
    assert original["c"][2]["d"] == "p\r\nq"


def test_list_top_level_and_cr_conversion():
    original_list = ["one", "line\r\ntwo", "three\rfour", "no newline"]
    original_copy = list(original_list)

    result = _convert_to_yaml_literal_string(original_list)

    # Original must be unchanged
    assert original_list == original_copy

    # Result assertions: only elements with LF (including CRLF) become LSS and CRLF normalized
    assert isinstance(result, list)
    assert isinstance(result[0], str) and not isinstance(result[0], LSS)
    # CRLF contains '\n' so gets normalized and converted
    assert isinstance(result[1], LSS) and str(result[1]) == "line\ntwo"
    # CR-only does not contain '\n' so it is left as-is (no normalization)
    assert isinstance(result[2], str) and not isinstance(result[2], LSS)
    assert result[2] == "three\rfour"
    assert isinstance(result[3], str) and not isinstance(result[3], LSS)


def test_string_top_level_is_converted_and_normalized():
    s_crlf = "first\r\nsecond"
    s_cr = "one\rtwo"
    s_lf = "a\nb"
    s_plain = "singleline"

    res_crlf = _convert_to_yaml_literal_string(s_crlf)
    res_cr = _convert_to_yaml_literal_string(s_cr)
    res_lf = _convert_to_yaml_literal_string(s_lf)
    res_plain = _convert_to_yaml_literal_string(s_plain)

    # CRLF should be normalized to LF and wrapped in LSS
    assert isinstance(res_crlf, LSS)
    assert str(res_crlf) == "first\nsecond"

    # CR-only does not contain '\n' so it should NOT be converted nor normalized
    assert isinstance(res_cr, str) and not isinstance(res_cr, LSS)
    assert res_cr == "one\rtwo"

    # LF input should be wrapped in LSS
    assert isinstance(res_lf, LSS)
    assert str(res_lf) == "a\nb"

    # Plain single-line string should remain a plain str
    assert isinstance(res_plain, str) and not isinstance(res_plain, LSS)
    assert res_plain == "singleline"
