import pytest
from typing import Union, List, Any as TypingAny

from gpt_researcher.config.config import Config


def test_union_none_round_024():
    # Union[str, None] with a None-like value should return None
    assert Config.convert_env_value("some_key", "None", Union[str, None]) is None


def test_union_int_str_round_024():
    # Union[int, str] should prefer int conversion when valid
    result = Config.convert_env_value("k", "123", Union[int, str])
    assert isinstance(result, int) and result == 123


def test_union_int_float_fallback_round_024():
    # For Union[int, float], an env value like "1.5" fails int() then succeeds as float
    result = Config.convert_env_value("k", "1.5", Union[int, float])
    assert isinstance(result, float) and result == 1.5


def test_union_all_fail_raises_round_024():
    # If all Union alternatives fail conversion, a ValueError must be raised
    with pytest.raises(ValueError):
        # int("bad") raises ValueError and json.loads("bad") raises JSONDecodeError (subclass of ValueError)
        Config.convert_env_value("k", "bad", Union[int, dict])


def test_bool_variants_round_024():
    # Truthy values recognized
    assert Config.convert_env_value("k", "True", bool) is True
    assert Config.convert_env_value("k", "1", bool) is True
    # Non-truthy value returns False
    assert Config.convert_env_value("k", "no", bool) is False


def test_numeric_str_any_round_024():
    # int and float conversions
    assert Config.convert_env_value("k", "42", int) == 42
    assert Config.convert_env_value("k", "3.14", float) == 3.14
    # str and typing.Any return the raw env value string
    assert Config.convert_env_value("k", "hello", str) == "hello"
    assert Config.convert_env_value("k", "world", TypingAny) == "world"


def test_list_and_dict_round_024():
    # JSON list parsing for typing.List[...] origin
    assert Config.convert_env_value("k", "[1, 2]", List[int]) == [1, 2]
    # dict type uses json.loads
    assert Config.convert_env_value("k", '{"a": 1}', dict) == {"a": 1}


def test_unsupported_type_raises_round_024():
    # Unsupported built-in type should raise ValueError
    with pytest.raises(ValueError):
        Config.convert_env_value("k", "irrelevant", tuple)
