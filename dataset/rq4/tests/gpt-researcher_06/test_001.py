def test_probe_001_uppercase_scheme_case_insensitive():
    """Probe: uppercase URL scheme should be treated identically to lowercase.

    Invariant: scheme matching is case-insensitive — an uppercase 'HTTPS://' must
    select the same transport and forward the url and headers as if 'https://'.
    """

    # Local deterministic inputs
    connection_url = "HTTPS://mcp.example.com"
    connection_headers = {"Authorization": "Bearer TOKEN"}
    configs = [{
        "name": "my_server",
        "connection_url": connection_url,
        "connection_headers": connection_headers,
    }]

    # Exercise the public entrypoint
    from gpt_researcher.mcp.client import MCPClientManager

    manager = MCPClientManager(configs)
    result = manager.convert_configs_to_langchain_format()

    # Basic structural expectations
    assert "my_server" in result, "expected server name 'my_server' in result"
    server = result["my_server"]

    # Primary behavioral oracle (single assertion the test stands/falls on)
    assert server.get("transport") == "streamable_http" and server.get("url") == connection_url and server.get("headers") == connection_headers, (
        f"Expected transport 'streamable_http', url '{connection_url}', and headers {connection_headers}; got: {server}"
    )
