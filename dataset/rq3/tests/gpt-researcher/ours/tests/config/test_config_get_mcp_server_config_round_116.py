import pytest

from gpt_researcher.config.config import Config


# We instantiate Config objects without calling __init__ to avoid file I/O or other side effects.
# Then we set the mcp_servers attribute directly to exercise get_mcp_server_config branches.


def make_config_with_servers(servers):
    cfg = object.__new__(Config)
    # ensure the attribute exists exactly as the implementation expects
    cfg.mcp_servers = servers
    return cfg


def test_get_mcp_server_config_empty_name_round_116():
    # Empty name should trigger the early return {}
    cfg = make_config_with_servers([{"name": "a"}])
    result = cfg.get_mcp_server_config("")
    assert result == {}, "Expected empty dict when name is falsy"


def test_get_mcp_server_config_no_servers_round_116():
    # No servers configured should trigger the early return {}
    cfg = make_config_with_servers([])
    result = cfg.get_mcp_server_config("server1")
    assert result == {}, "Expected empty dict when mcp_servers is empty"


def test_get_mcp_server_config_non_dict_entry_round_116():
    # A non-dict entry should be skipped (isinstance check false) and ultimately return {}
    cfg = make_config_with_servers(["not-a-dict"])
    result = cfg.get_mcp_server_config("server1")
    assert result == {}, "Non-dict entries must be ignored and result should be empty dict"


def test_get_mcp_server_config_mismatched_dict_name_round_116():
    # A dict with a different name should be skipped and loop should finish returning {}
    cfg = make_config_with_servers([{"name": "other"}])
    result = cfg.get_mcp_server_config("server1")
    assert result == {}, "Dict entries with non-matching name should not be returned"


def test_get_mcp_server_config_matching_server_round_116():
    # When a dict with matching name is present, it should be returned as-is
    matching = {"name": "server1", "url": "https://example"}
    cfg = make_config_with_servers([
        "not-a-dict",
        {"name": "other"},
        matching,
    ])
    result = cfg.get_mcp_server_config("server1")
    # Ensure the returned object is exactly the matching dict (identity not required, but content must match)
    assert result == matching
