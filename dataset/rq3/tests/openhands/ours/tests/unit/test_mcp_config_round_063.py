import pytest

from openhands.core.config.mcp_config import MCPStdioServerConfig


def test_parse_env_whitespace_round_063():
    # empty/whitespace string should return empty dict (covers early return branch)
    res = MCPStdioServerConfig.parse_env("   ")
    assert isinstance(res, dict)
    assert res == {}


def test_parse_env_single_pair_round_063():
    # single KEY=VALUE pair should be parsed into dict
    res = MCPStdioServerConfig.parse_env("KEY=VALUE")
    assert res == {"KEY": "VALUE"}


def test_parse_env_multiple_with_empty_round_063():
    # multiple pairs with extra spaces and an empty pair (", ,") should skip empty entries
    s = " A=1,  ,B=2 "
    res = MCPStdioServerConfig.parse_env(s)
    # ensure both keys present and values preserved; order not important
    assert res == {"A": "1", "B": "2"}


def test_parse_env_missing_equal_round_063():
    # a pair without '=' should raise ValueError with explanatory message
    with pytest.raises(ValueError) as excinfo:
        MCPStdioServerConfig.parse_env("NOEQ")
    assert "must be in KEY=VALUE format" in str(excinfo.value)


def test_parse_env_empty_key_round_063():
    # a pair with an empty key ("=value") should raise a specific ValueError
    with pytest.raises(ValueError) as excinfo:
        MCPStdioServerConfig.parse_env("=value")
    assert "Environment variable key cannot be empty" in str(excinfo.value)


def test_parse_env_invalid_key_round_063():
    # key starting with a digit is invalid according to the regex and should raise
    with pytest.raises(ValueError) as excinfo:
        MCPStdioServerConfig.parse_env("1BAD=2")
    msg = str(excinfo.value)
    assert "Invalid environment variable name" in msg
    # also assert the offending key appears in the message for clarity
    assert "1BAD" in msg


def test_parse_env_non_str_and_none_round_063():
    # non-string input should be returned as-is (or empty dict for falsy values)
    input_dict = {"A": "B"}
    res = MCPStdioServerConfig.parse_env(input_dict)
    assert res is input_dict or res == input_dict

    # None should be normalized to empty dict by the final `return v or {}`
    res_none = MCPStdioServerConfig.parse_env(None)
    assert res_none == {}
