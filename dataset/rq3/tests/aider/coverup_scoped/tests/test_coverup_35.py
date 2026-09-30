# file: aider/coders/base_coder.py:2338-2363
# asked: {"lines": [2341, 2342, 2343, 2345, 2346, 2347, 2348, 2350, 2351, 2352, 2353, 2355, 2356, 2357, 2358, 2360, 2361, 2362, 2363], "branches": [[2342, 2343], [2342, 2345]]}
# gained: {"lines": [2341, 2342, 2343, 2345, 2346, 2347, 2348, 2350, 2351, 2352, 2353, 2355, 2356, 2357, 2358, 2360, 2361], "branches": [[2342, 2343], [2342, 2345]]}

import types
import pytest
from aider.coders.base_coder import Coder


def call_with_args(arguments):
    fake = types.SimpleNamespace(partial_response_function_call={"arguments": arguments})
    # call the unbound function on a fake self to avoid needing a full Coder instance
    return Coder.parse_partial_args(fake)


def test_parse_partial_args_no_arguments_key():
    fake = types.SimpleNamespace(partial_response_function_call={})
    # Should return None when 'arguments' is missing
    assert Coder.parse_partial_args(fake) is None

    # And also when 'arguments' is an empty string
    fake2 = types.SimpleNamespace(partial_response_function_call={"arguments": ""})
    assert Coder.parse_partial_args(fake2) is None


def test_parse_partial_args_valid_json():
    res = call_with_args('{"a": 1, "b": [true, false, null]}')
    assert isinstance(res, dict)
    assert res["a"] == 1
    assert res["b"] == [True, False, None]


def test_parse_partial_args_fix_append_bracket_and_brace():
    # Original is missing the closing of array and object: '{"a":[1,2'
    # Appending ']}'' should produce '{"a":[1,2]}' which is valid JSON
    res = call_with_args('{"a":[1,2')
    assert res == {"a": [1, 2]}


def test_parse_partial_args_fix_append_closing_object_and_array():
    # Original: '{"a":[{"b":1' -> appending '}]}'' yields '{"a":[{"b":1}]}' valid JSON
    res = call_with_args('{"a":[{"b":1')
    assert res == {"a": [{"b": 1}]}


def test_parse_partial_args_fix_append_quote_and_closures():
    # Original: '{"a":[{"b":"c' -> appending '"}]}' yields '{"a":[{"b":"c"}]}' valid JSON
    res = call_with_args('{"a":[{"b":"c')
    assert res == {"a": [{"b": "c"}]}
