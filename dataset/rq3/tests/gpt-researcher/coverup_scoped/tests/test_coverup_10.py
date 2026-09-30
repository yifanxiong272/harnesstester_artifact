# file: gpt_researcher/mcp/client.py:40-103
# asked: {"lines": [40, 47, 49, 51, 54, 57, 58, 59, 60, 61, 62, 63, 64, 67, 68, 69, 70, 73, 74, 76, 77, 78, 79, 82, 83, 84, 87, 88, 89, 90, 93, 94, 95, 98, 99, 101, 103], "branches": [[49, 51], [49, 103], [58, 59], [58, 73], [59, 60], [59, 62], [62, 63], [62, 67], [69, 70], [69, 76], [76, 77], [76, 82], [78, 79], [78, 82], [82, 83], [82, 98], [83, 84], [83, 98], [88, 89], [88, 90], [94, 95], [94, 98], [98, 99], [98, 101]]}
# gained: {"lines": [40, 47, 49, 51, 54, 57, 58, 59, 60, 61, 62, 63, 64, 67, 68, 69, 70, 73, 74, 76, 82, 83, 84, 87, 88, 89, 90, 93, 94, 95, 98, 99, 101, 103], "branches": [[49, 51], [49, 103], [58, 59], [58, 73], [59, 60], [59, 62], [62, 63], [62, 67], [69, 70], [76, 82], [82, 83], [82, 98], [83, 84], [88, 89], [88, 90], [94, 95], [94, 98], [98, 99], [98, 101]]}

import pytest

from gpt_researcher.mcp.client import MCPClientManager


def test_convert_various_transports_and_tokens():
    """
    Test multiple configurations to exercise websocket, https (streamable_http),
    and non-standard URL with explicit connection_type (http).
    Also verify default server name generation and token propagation.
    """
    configs = [
        {
            "name": "ws_server",
            "connection_url": "wss://example.org/socket",
            "connection_token": "token_ws",
        },
        {
            # no name to trigger default naming (mcp_server_2)
            "connection_url": "https://api.example.org/endpoint",
        },
        {
            "name": "custom_http",
            "connection_url": "customproto://host/path",
            "connection_type": "http",
        },
    ]

    mgr = MCPClientManager(configs)
    out = mgr.convert_configs_to_langchain_format()

    # Ensure all servers present
    assert "ws_server" in out
    # second entry should have default generated name
    assert "mcp_server_2" in out
    assert "custom_http" in out

    # websocket server assertions
    ws_cfg = out["ws_server"]
    assert ws_cfg.get("transport") == "websocket"
    assert ws_cfg.get("url") == "wss://example.org/socket"
    # token should be propagated
    assert ws_cfg.get("token") == "token_ws"

    # https -> streamable_http
    https_cfg = out["mcp_server_2"]
    assert https_cfg.get("transport") == "streamable_http"
    assert https_cfg.get("url") == "https://api.example.org/endpoint"

    # custom proto with connection_type http should include url and transport 'http'
    custom_cfg = out["custom_http"]
    assert custom_cfg.get("transport") == "http"
    # because connection_type is one of ["websocket","streamable_http","http"], url should be set
    assert custom_cfg.get("url") == "customproto://host/path"


def test_stdio_command_args_env_and_args_string_vs_list():
    """
    Test stdio transport handling:
    - command provided
    - args when provided as string should be split into list
    - args when provided as list should be preserved
    - env dict should be propagated
    - token should be added when present
    """
    configs = [
        {
            "name": "stdio_with_str_args",
            "connection_type": "stdio",
            "command": "/usr/bin/myserver",
            "args": "--opt1 val1 --flag",
            "env": {"KEY": "VALUE"},
            "connection_token": "tokstdio",
        },
        {
            "name": "stdio_with_list_args",
            # omit connection_type and connection_url to force default stdio handling
            "command": "/usr/bin/other",
            "args": ["--a", "1", "--b", "2"],
            "env": {},
        },
    ]

    mgr = MCPClientManager(configs)
    out = mgr.convert_configs_to_langchain_format()

    s1 = out["stdio_with_str_args"]
    assert s1.get("transport") == "stdio"
    assert s1.get("command") == "/usr/bin/myserver"
    # args originally a string should be split into a list
    assert isinstance(s1.get("args"), list)
    assert s1["args"] == ["--opt1", "val1", "--flag"]
    # env should be propagated
    assert s1.get("env") == {"KEY": "VALUE"}
    # token propagated
    assert s1.get("token") == "tokstdio"

    s2 = out["stdio_with_list_args"]
    assert s2.get("transport") == "stdio"
    assert s2.get("command") == "/usr/bin/other"
    # list args preserved
    assert isinstance(s2.get("args"), list)
    assert s2["args"] == ["--a", "1", "--b", "2"]
    # empty env should not appear or be empty dict if present
    if "env" in s2:
        assert s2["env"] == {}
