import pytest

from openhands.core.config.mcp_config import MCPStdioServerConfig


def test_parse_env_whitespace_round_063():
    # whitespace-only string should return empty dict
    result = MCPStdioServerConfig.parse_env("   ")
    assert result == {}


def test_parse_env_simple_pair_round_063():
    # single KEY=VALUE pair parses to a dict
    result = MCPStdioServerConfig.parse_env("FOO=bar")
    assert result == {"FOO": "bar"}


def test_parse_env_multiple_pairs_and_empty_pair_round_063():
    # multiple pairs with extra commas/empty entries are tolerated and skipped
    s = "A=1,,B=2, ,C=3"
    result = MCPStdioServerConfig.parse_env(s)
    assert result == {"A": "1", "B": "2", "C": "3"}


def test_parse_env_missing_equals_raises_round_063():
    # a pair without '=' should raise a ValueError mentioning KEY=VALUE format
    with pytest.raises(ValueError) as exc:
        MCPStdioServerConfig.parse_env("JUSTAKEY")
    assert "must be in KEY=VALUE format" in str(exc.value)


def test_parse_env_empty_key_raises_round_063():
    # a pair like =value should raise for empty key
    with pytest.raises(ValueError) as exc:
        MCPStdioServerConfig.parse_env("=value")
    assert "Environment variable key cannot be empty" in str(exc.value)


def test_parse_env_invalid_key_name_raises_round_063():
    # keys must start with a letter or underscore; starting with digit is invalid
    with pytest.raises(ValueError) as exc:
        MCPStdioServerConfig.parse_env("1BAD=1")
    msg = str(exc.value)
    assert "Invalid environment variable name" in msg
    assert "1BAD" in msg


def test_parse_env_non_str_and_dict_passthrough_round_063():
    # non-string falsy values (e.g., None) return empty dict
    assert MCPStdioServerConfig.parse_env(None) == {}

    # dicts are returned as-is
    d = {"X": "Y"}
    assert MCPStdioServerConfig.parse_env(d) is d
