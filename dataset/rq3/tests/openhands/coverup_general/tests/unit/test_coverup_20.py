# file: openhands/runtime/impl/action_execution/action_execution_client.py:372-461
# asked: {"lines": [375, 378, 380, 381, 384, 387, 388, 390, 391, 394, 395, 396, 397, 400, 401, 402, 406, 409, 410, 411, 412, 414, 415, 417, 419, 420, 421, 423, 424, 425, 426, 427, 429, 430, 431, 433, 434, 435, 436, 440, 441, 442, 443, 445, 446, 447, 450, 452, 454, 455, 456, 457, 461], "branches": [[378, 380], [378, 384], [390, 391], [390, 394], [406, 409], [406, 450], [410, 411], [410, 414], [411, 410], [411, 412], [430, 431], [430, 433], [433, 434], [433, 440], [452, 454], [452, 461]]}
# gained: {"lines": [375, 378, 380, 381, 384, 387, 388, 390, 391, 394, 395, 396, 397, 400, 401, 402, 406, 409, 410, 411, 412, 414, 415, 417, 419, 420, 421, 423, 424, 425, 426, 427, 429, 430, 431, 433, 434, 435, 436, 440, 441, 442, 443, 445, 446, 447, 450, 452, 454, 455, 456, 457, 461], "branches": [[378, 380], [378, 384], [390, 391], [390, 394], [406, 409], [406, 450], [410, 411], [410, 414], [411, 412], [430, 431], [430, 433], [433, 434], [452, 454], [452, 461]]}

import sys
import types
import pytest

from openhands.runtime.impl.action_execution.action_execution_client import ActionExecutionClient
from openhands.core.config.mcp_config import MCPSSEServerConfig


class DummyStdio:
    def __init__(self, name):
        self.name = name

    def model_dump(self, mode='json'):
        return {'name': self.name}

    def __eq__(self, other):
        return isinstance(other, DummyStdio) and self.name == other.name

    def __repr__(self):
        return f"DummyStdio({self.name})"


class MockConfigContainer:
    def __init__(self, stdio_servers=None, sse_servers=None):
        self.stdio_servers = list(stdio_servers or [])
        self.sse_servers = list(sse_servers or [])

    def model_copy(self):
        return MockConfigContainer(stdio_servers=list(self.stdio_servers), sse_servers=list(self.sse_servers))

    def __repr__(self):
        return f"MockConfigContainer(stdio_servers={self.stdio_servers}, sse_servers={self.sse_servers})"


class DummyResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ''):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        return self._json_data


def ensure_platform(monkeypatch, value):
    monkeypatch.setattr(sys, 'platform', value, raising=False)


def log_contains(fake_self, level: str, substring: str) -> bool:
    return any(lvl == level and substring in msg for (lvl, msg) in getattr(fake_self, "logged", []))


def make_fake_self(mcp_config: MockConfigContainer):
    # Create a minimal object with attributes expected by get_mcp_config
    fake = types.SimpleNamespace()
    fake.config = types.SimpleNamespace(mcp=mcp_config)
    fake._last_updated_mcp_stdio_servers = []
    fake.action_execution_server_url = "https://example.com/"
    fake.session_api_key = "secret-key"
    fake.logged = []

    def log(level, message):
        fake.logged.append((level, message))

    fake.log = log

    # default request sender: returns 200 OK with empty body
    fake._send_action_server_request = lambda method, url, **kwargs: DummyResponse(200, {})
    return fake


def call_get_mcp_config(fake, extra_stdio_servers=None):
    # Call the unbound function with our fake object as self
    return ActionExecutionClient.get_mcp_config(fake, extra_stdio_servers)


def test_get_mcp_config_windows(monkeypatch):
    ensure_platform(monkeypatch, 'win32')
    mcp = MockConfigContainer(stdio_servers=[], sse_servers=[])
    fake = make_fake_self(mcp)

    result = call_get_mcp_config(fake)

    assert hasattr(result, 'stdio_servers')
    assert hasattr(result, 'sse_servers')
    assert result.stdio_servers == []
    assert result.sse_servers == []
    assert log_contains(fake, 'debug', 'MCP is disabled on Windows, returning empty config')


def test_get_mcp_config_no_new_servers(monkeypatch):
    ensure_platform(monkeypatch, 'linux')
    mcp = MockConfigContainer(stdio_servers=[], sse_servers=[])
    fake = make_fake_self(mcp)

    result = call_get_mcp_config(fake)

    assert result.sse_servers == []
    assert log_contains(fake, 'debug', 'No new stdio servers to update')


def test_get_mcp_config_update_failure(monkeypatch):
    ensure_platform(monkeypatch, 'linux')
    mcp = MockConfigContainer(stdio_servers=[], sse_servers=[])
    fake = make_fake_self(mcp)

    extra = [DummyStdio('alpha')]

    def fake_request(method, url, **kwargs):
        return DummyResponse(500, json_data={'ok': False}, text='server-error')

    fake._send_action_server_request = fake_request

    result = call_get_mcp_config(fake, extra_stdio_servers=extra)

    # _last_updated_mcp_stdio_servers should remain empty after failed update
    assert fake._last_updated_mcp_stdio_servers == []
    assert log_contains(fake, 'warning', 'Failed to update MCP server: server-error')
    assert result.sse_servers == []


def test_get_mcp_config_update_success_with_router_error_and_union(monkeypatch):
    ensure_platform(monkeypatch, 'linux')
    existing = DummyStdio('existing')
    mcp = MockConfigContainer(stdio_servers=[existing], sse_servers=[])
    fake = make_fake_self(mcp)

    # fake already tracked one old server
    old = DummyStdio('old')
    fake._last_updated_mcp_stdio_servers = [old]

    new = DummyStdio('new')
    extra = [new]

    def fake_request(method, url, **kwargs):
        sent_json = kwargs.get('json')
        assert isinstance(sent_json, list)
        names = [d.get('name', '') for d in sent_json]
        # Ensure the list is sorted by name
        assert sorted(names) == names
        return DummyResponse(200, json_data={'router_error_log': 'some router issue'})

    fake._send_action_server_request = fake_request

    result = call_get_mcp_config(fake, extra_stdio_servers=extra)

    names_tracked = [s.name for s in fake._last_updated_mcp_stdio_servers]
    assert set(names_tracked) == {'existing', 'new', 'old'}
    assert len(fake._last_updated_mcp_stdio_servers) == 3

    assert log_contains(fake, 'warning', 'Some MCP servers failed to be added')
    assert log_contains(fake, 'debug', 'Successfully updated MCP stdio servers, now tracking')
    assert log_contains(fake, 'info', 'Updated MCP config:')

    # Verify SSE server appended to returned config
    assert len(result.sse_servers) == 1
    sse = result.sse_servers[0]
    assert isinstance(sse, MCPSSEServerConfig)
    assert getattr(sse, 'url') == fake.action_execution_server_url.rstrip('/') + '/mcp/sse'
    assert getattr(sse, 'api_key') == fake.session_api_key
