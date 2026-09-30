# file: openhands/mcp/client.py:59-125
# asked: {"lines": [66, 67, 69, 70, 72, 73, 74, 75, 76, 77, 79, 80, 83, 84, 87, 88, 89, 90, 93, 94, 95, 98, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 112, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 125], "branches": [[69, 70], [69, 72], [83, 84], [83, 87], [87, 88], [87, 93]]}
# gained: {"lines": [66, 67, 69, 70, 72, 73, 74, 75, 76, 77, 79, 80, 83, 84, 87, 88, 89, 90, 93, 94, 95, 98, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 114, 115, 116, 117, 118, 119, 120, 122, 123, 125], "branches": [[69, 70], [69, 72], [83, 84], [83, 87], [87, 88], [87, 93]]}

import pytest
import types

import openhands.mcp.client as client_module
from openhands.core.config.mcp_config import MCPSHTTPServerConfig, MCPSSEServerConfig


@pytest.mark.asyncio
async def test_connect_http_success_http_transport(monkeypatch):
    created = {}

    class FakeStreamableHttpTransport:
        def __init__(self, url, headers=None):
            created['transport_class'] = 'streamable'
            created['url'] = url
            created['headers'] = headers

    class FakeSSETransport:
        def __init__(self, url, headers=None):
            created['transport_class'] = 'sse'
            created['url'] = url
            created['headers'] = headers

    class FakeClient:
        def __init__(self, transport, timeout):
            # emulate real client shape minimally
            self.transport = transport
            self.timeout = timeout

    async def fake_initialize(self):
        # mark that initialization was called
        created['initialized'] = True

    # Patch transports and client in the module under test
    monkeypatch.setattr(client_module, 'StreamableHttpTransport', FakeStreamableHttpTransport)
    monkeypatch.setattr(client_module, 'SSETransport', FakeSSETransport)
    monkeypatch.setattr(client_module, 'Client', FakeClient)
    monkeypatch.setattr(client_module.MCPClient, '_initialize_and_list_tools', fake_initialize, raising=False)

    server = MCPSHTTPServerConfig(url='http://example.com', api_key='my-api-key')
    mcp_client = client_module.MCPClient()

    await mcp_client.connect_http(server, conversation_id='conv-123', timeout=2.5)

    # Client was set and initialized
    assert isinstance(mcp_client.client, FakeClient)
    assert mcp_client.client.timeout == 2.5
    # Transport chosen should be StreamableHttpTransport and headers should include api key and conversation id
    assert created['transport_class'] == 'streamable'
    assert created['url'] == 'http://example.com'
    headers = created['headers']
    assert headers is not None
    assert headers['Authorization'] == 'Bearer my-api-key'
    assert headers['s'] == 'my-api-key'
    assert headers['X-Session-API-Key'] == 'my-api-key'
    assert headers['X-OpenHands-ServerConversation-ID'] == 'conv-123'
    assert created.get('initialized', False) is True


@pytest.mark.asyncio
async def test_connect_http_sse_no_api_key_and_mcp_error(monkeypatch):
    created = {}

    class FakeSSETransport:
        def __init__(self, url, headers=None):
            created['transport_class'] = 'sse'
            created['url'] = url
            created['headers'] = headers

    class FakeClient:
        def __init__(self, transport, timeout):
            self.transport = transport
            self.timeout = timeout

    async def raise_mcp_error(self):
        # McpError expects an object with a .message attribute
        err_obj = types.SimpleNamespace(message='mcp-failure')
        raise client_module.McpError(err_obj)

    calls = []

    def fake_add_error(server_name, server_type, error_message, exception_details=None):
        calls.append({
            'server_name': server_name,
            'server_type': server_type,
            'error_message': error_message,
            'exception_details': exception_details,
        })

    monkeypatch.setattr(client_module, 'SSETransport', FakeSSETransport)
    monkeypatch.setattr(client_module, 'Client', FakeClient)
    monkeypatch.setattr(client_module.MCPClient, '_initialize_and_list_tools', raise_mcp_error, raising=False)
    # Patch the global error collector instance's add_error
    monkeypatch.setattr(client_module.mcp_error_collector, 'add_error', fake_add_error)

    server = MCPSSEServerConfig(url='http://sse.example', api_key=None)
    mcp_client = client_module.MCPClient()

    with pytest.raises(client_module.McpError):
        await mcp_client.connect_http(server, timeout=1.0)

    # add_error should be called once with server_type 'sse'
    assert len(calls) == 1
    call = calls[0]
    assert call['server_name'] == 'http://sse.example'
    assert call['server_type'] == 'sse'
    assert 'mcp-failure' in call['error_message'] or 'mcp-failure' in (call['exception_details'] or '')


@pytest.mark.asyncio
async def test_connect_http_http_generic_exception_records_error_and_reraises(monkeypatch):
    created = {}

    class FakeStreamableHttpTransport:
        def __init__(self, url, headers=None):
            created['transport_class'] = 'streamable'
            created['url'] = url
            created['headers'] = headers

    class FakeClient:
        def __init__(self, transport, timeout):
            self.transport = transport
            self.timeout = timeout

    async def raise_value_error(self):
        raise ValueError('something went wrong')

    calls = []

    def fake_add_error(server_name, server_type, error_message, exception_details=None):
        calls.append({
            'server_name': server_name,
            'server_type': server_type,
            'error_message': error_message,
            'exception_details': exception_details,
        })

    monkeypatch.setattr(client_module, 'StreamableHttpTransport', FakeStreamableHttpTransport)
    monkeypatch.setattr(client_module, 'Client', FakeClient)
    monkeypatch.setattr(client_module.MCPClient, '_initialize_and_list_tools', raise_value_error, raising=False)
    monkeypatch.setattr(client_module.mcp_error_collector, 'add_error', fake_add_error)

    server = MCPSHTTPServerConfig(url='http://http.example', api_key='k')
    mcp_client = client_module.MCPClient()

    with pytest.raises(ValueError):
        await mcp_client.connect_http(server)

    # add_error should be called once and server_type must be 'shttp' for MCPSHTTPServerConfig
    assert len(calls) == 1
    call = calls[0]
    assert call['server_name'] == 'http://http.example'
    assert call['server_type'] == 'shttp'
    assert 'something went wrong' in (call['error_message'] or '') or 'something went wrong' in (call['exception_details'] or '')


@pytest.mark.asyncio
async def test_connect_http_raises_value_error_when_no_url_on_server_like_object():
    # Create a minimal server-like object without a URL (falsy) that is NOT an MCPS*Config instance.
    class DummyServer:
        def __init__(self):
            self.url = ''
            self.api_key = None

    mcp_client = client_module.MCPClient()
    server = DummyServer()
    with pytest.raises(ValueError):
        await mcp_client.connect_http(server)
