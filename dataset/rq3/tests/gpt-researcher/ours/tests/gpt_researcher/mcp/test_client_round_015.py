import pytest

from gpt_researcher.mcp.client import MCPClientManager


def test_websocket_and_token_round_015():
    configs = [
        {
            # no explicit name -> should default to mcp_server_1
            "connection_url": "wss://example.com/path",
            "connection_token": "secrettoken123",
        }
    ]

    mgr = MCPClientManager(mcp_configs=configs)
    out = mgr.convert_configs_to_langchain_format()

    # Should have one server with default name
    assert "mcp_server_1" in out
    server = out["mcp_server_1"]

    # websocket transport and url must be set
    assert server.get("transport") == "websocket"
    assert server.get("url") == "wss://example.com/path"

    # token should be propagated
    assert server.get("token") == "secrettoken123"


def test_stdio_command_args_env_string_round_015():
    configs = [
        {
            "name": "local_stdio",
            # no connection_url -> stdio transport expected
            "command": "/usr/bin/fake-server",
            # args as string should be split
            "args": "--mode fast --retry 3",
            "env": {"KEY": "VALUE"},
        }
    ]

    mgr = MCPClientManager(mcp_configs=configs)
    out = mgr.convert_configs_to_langchain_format()

    assert "local_stdio" in out
    server = out["local_stdio"]

    # transport should be stdio when no connection_url provided
    assert server.get("transport") == "stdio"

    # command, args (split), and env should be present
    assert server.get("command") == "/usr/bin/fake-server"
    assert server.get("args") == ["--mode", "fast", "--retry", "3"]
    assert server.get("env") == {"KEY": "VALUE"}


def test_stdio_args_list_no_env_round_015():
    configs = [
        {
            "name": "local_stdio_list",
            "command": "run-server",
            # args already a list should be preserved
            "args": ["--one", "two"],
            # no env provided -> no env key in resulting config
        }
    ]

    mgr = MCPClientManager(mcp_configs=configs)
    out = mgr.convert_configs_to_langchain_format()

    assert "local_stdio_list" in out
    server = out["local_stdio_list"]

    assert server.get("transport") == "stdio"
    assert server.get("command") == "run-server"
    assert server.get("args") == ["--one", "two"]
    assert "env" not in server


def test_custom_protocol_with_http_connection_type_and_name_round_015():
    # connection_url that does not match ws/http prefixes should hit the fallback
    configs = [
        {
            "name": "custom_http",
            "connection_url": "customproto://host.example",
            "connection_type": "http",
        }
    ]

    mgr = MCPClientManager(mcp_configs=configs)
    out = mgr.convert_configs_to_langchain_format()

    assert "custom_http" in out
    server = out["custom_http"]

    # transport should be set to the provided connection_type
    assert server.get("transport") == "http"

    # Because connection_type is in ["websocket","streamable_http","http"],
    # the code places the URL on the server config
    assert server.get("url") == "customproto://host.example"


def test_https_streamable_http_round_015():
    configs = [
        {
            "connection_url": "https://api.example/v1",
            # ensure naming default
        }
    ]

    mgr = MCPClientManager(mcp_configs=configs)
    out = mgr.convert_configs_to_langchain_format()

    assert "mcp_server_1" in out
    server = out["mcp_server_1"]

    # https should map to streamable_http
    assert server.get("transport") == "streamable_http"
    assert server.get("url") == "https://api.example/v1"
