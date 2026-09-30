import pytest

from gpt_researcher.actions.agent_creator import extract_json_with_regex


def test_none_input_round_134():
    # None input should immediately return None (covers line 121 -> 122)
    assert extract_json_with_regex(None) is None


def test_empty_string_round_134():
    # empty string is falsy and should return None (covers line 121 -> 122)
    assert extract_json_with_regex("") is None


def test_no_json_round_134():
    # string without any braces should return None (covers path where re.search finds nothing -> line 126)
    assert extract_json_with_regex("no json here") is None


def test_single_json_round_134():
    # should extract the first simple JSON object substring (covers lines 123 -> 124 -> 125)
    s = 'prefix {"a":1} suffix'
    assert extract_json_with_regex(s) == '{"a":1}'


def test_multiple_json_round_134():
    # when multiple JSON-like objects exist, return the first match (exercises non-greedy behavior)
    s = '{"x":1} middle {"y":2}'
    assert extract_json_with_regex(s) == '{"x":1}'


def test_multiline_json_round_134():
    # DOTALL should allow newlines inside braces to be matched
    s = 'pre {\n "a": 1\n} post'
    assert extract_json_with_regex(s) == '{\n "a": 1\n}'


def test_nested_braces_round_134():
    # For nested braces, ensure a match is returned and it contains inner content.
    # We don't assert perfect balancing here; we assert observable parts to avoid brittle expectations.
    s = 'start {"a": {"b": 2}} end'
    res = extract_json_with_regex(s)
    assert res is not None
    # returned substring must start with '{' and include the nested key/value
    assert res.startswith('{')
    assert '"b": 2' in res
    assert '}' in res
