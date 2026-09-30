import json
from aider.coders import base_coder


# Create minimal Coder instances without invoking heavy __init__
# we use __new__ and set only the attribute used by parse_partial_args


def test_parse_partial_args_none_round_082():
    coder = base_coder.Coder.__new__(base_coder.Coder)
    # no 'arguments' key -> get() returns None -> method should return None
    coder.partial_response_function_call = {}
    result = coder.parse_partial_args()
    assert result is None


def test_parse_partial_args_valid_json_round_082():
    coder = base_coder.Coder.__new__(base_coder.Coder)
    coder.partial_response_function_call = {"arguments": '{"x": 42}'}
    result = coder.parse_partial_args()
    # direct valid JSON should parse correctly
    assert isinstance(result, dict)
    assert result == {"x": 42}


def test_parse_partial_args_close_array_round_082():
    coder = base_coder.Coder.__new__(base_coder.Coder)
    # This string is invalid JSON alone, but adding ']}' should make it valid: '{"a": [1' + ']}' -> '{"a": [1]}'
    coder.partial_response_function_call = {"arguments": '{"a": [1'}
    result = coder.parse_partial_args()
    assert result == {"a": [1]}


def test_parse_partial_args_close_object_in_array_round_082():
    coder = base_coder.Coder.__new__(base_coder.Coder)
    # This string is invalid alone; appending '}]}' should close inner object and outer array/object:
    # '{"a": [{"b":2' + '}]}' -> '{"a": [{"b":2}]}'
    coder.partial_response_function_call = {"arguments": '{"a": [{"b":2'}
    result = coder.parse_partial_args()
    assert result == {"a": [{"b": 2}]}


def test_parse_partial_args_all_attempts_fail_round_082():
    coder = base_coder.Coder.__new__(base_coder.Coder)
    # a string that will not become valid JSON with any of the attempted suffixes
    coder.partial_response_function_call = {"arguments": 'not-a-json-or-closable-structure'}
    result = coder.parse_partial_args()
    assert result is None
