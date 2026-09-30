import pytest

from gpt_researcher.mcp.client import MCPClientManager


def test_convert_configs_to_langchain_format_round_015():
    """
    Exercise multiple configuration permutations to cover transport detection,
    stdio handling (including splitting args), default server naming, and token
    propagation. This is deterministic and uses no network or external services.
    """
    configs = [
        # 0: explicit name, websocket URL, token
        {
            "name": "srv_ws",
            "connection_url": "wss://example.websocket",
            "connection_token": "token-ws",
        },
        # 1: no name, https URL, headers present (headers are expected NOT to be
        # attached because the implementation checks a different key for headers)
        {
            "connection_url": "https://example.http",
            "connection_headers": {"X-Test": "yes"},
        },
        # 2: non-HTTP/WS URL but connection_type indicates an HTTP-like transport
        {
            # no explicit name -> should become default mcp_server_3 (index 2 -> +1)
            "connection_url": "ftp://example.unknown",
            "connection_type": "http",
        },
        # 3: no URL -> stdio transport path, command present, args as string, env present
        {
            "name": "srv_stdio",
            "connection_type": "stdio",
            "command": "run",
            "args": "-a -b -c",
            "env": {"ENV1": "val1"},
            "connection_token": "token-stdio",
        },
    ]

    mgr = MCPClientManager(mcp_configs=configs)
    result = mgr.convert_configs_to_langchain_format()

    # Basic shape checks
    assert isinstance(result, dict)
    # 0: websocket entry (explicit name)
    assert "srv_ws" in result
    ws_cfg = result["srv_ws"]
    assert ws_cfg.get("transport") == "websocket"
    assert ws_cfg.get("url") == "wss://example.websocket"
    # token propagation
    assert ws_cfg.get("token") == "token-ws"

    # 1: https entry, default name mcp_server_2
    assert "mcp_server_2" in result
    https_cfg = result["mcp_server_2"]
    assert https_cfg.get("transport") == "streamable_http"
    assert https_cfg.get("url") == "https://example.http"
    # connection_headers are not attached by the implementation because it
    # checks server_config.get("connection_type") instead of transport
    assert "headers" not in https_cfg

    # 2: ftp URL with connection_type == 'http' should set transport to 'http' and url
    assert "mcp_server_3" in result
    ftp_cfg = result["mcp_server_3"]
    assert ftp_cfg.get("transport") == "http"
    assert ftp_cfg.get("url") == "ftp://example.unknown"

    # 3: stdio path with command, args as string should be split into list and env propagated
    assert "srv_stdio" in result
    stdio_cfg = result["srv_stdio"]
    assert stdio_cfg.get("transport") == "stdio"
    assert stdio_cfg.get("command") == "run"
    assert stdio_cfg.get("args") == ["-a", "-b", "-c"]
    assert stdio_cfg.get("env") == {"ENV1": "val1"}
    assert stdio_cfg.get("token") == "token-stdio"
