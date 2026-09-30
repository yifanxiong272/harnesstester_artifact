import asyncio
import json
import pytest

import backend.server.server_utils as su


class FakeWebsocket:
    def __init__(self):
        self.sent = []

    async def send_json(self, data):
        # store a deep copy-like structure (JSON-serializable objects only in this code path)
        self.sent.append(data)


@pytest.mark.asyncio
async def test_no_messages_round_044():
    """When the parsed JSON contains no message and no messages list, the function should send a 'No message provided.' response."""
    ws = FakeWebsocket()
    # Provide JSON with no message and no messages
    data = 'chat {}'

    # Ensure ChatAgentWithMemory exists so flow reaches the 'no messages' check first
    # but we don't want to actually construct an agent here; leave as None so code returns earlier
    monkeypatch_target = getattr(su, 'ChatAgentWithMemory', None)
    try:
        # Force it to something truthy so that the code does not short-circuit at ChatAgentWithMemory None check
        # But to hit the 'no messages' branch we simply ensure ChatAgentWithMemory is not consulted by returning early
        # The code checks messages before ChatAgentWithMemory, so leaving ChatAgentWithMemory alone is fine
        await su.handle_chat_command(ws, data)

        assert len(ws.sent) == 1
        payload = ws.sent[0]
        assert payload["type"] == "chat"
        assert payload["content"] == "No message provided."
        assert payload["role"] == "assistant"
    finally:
        # no change made to module-level ChatAgentWithMemory here, nothing to restore
        pass


@pytest.mark.asyncio
async def test_chat_unavailable_round_044(monkeypatch):
    """When a message is provided but ChatAgentWithMemory is None, the handler should inform the client chat is unavailable."""
    ws = FakeWebsocket()
    data = 'chat {"message": "hello"}'

    # Patch ChatAgentWithMemory to None to trigger the unavailable branch
    monkeypatch.setattr(su, 'ChatAgentWithMemory', None)

    await su.handle_chat_command(ws, data)

    assert len(ws.sent) == 1
    payload = ws.sent[0]
    assert payload["type"] == "chat"
    assert "Chat functionality is not available" in payload["content"]
    assert payload["role"] == "assistant"


@pytest.mark.asyncio
async def test_success_with_metadata_round_044(monkeypatch):
    """When ChatAgentWithMemory.chat returns a response and truthy tool metadata, the metadata should be placed under 'metadata' with key 'tool_calls'."""
    ws = FakeWebsocket()
    data = 'chat {"messages": [{"role": "user", "content": "hey"}]}'

    class FakeAgent:
        def __init__(self, report, config_path, headers):
            # assert constructor receives expected parameters from code under test
            assert config_path == "default"
            # store provided values for introspection if needed
            self.report = report
            self.config_path = config_path
            self.headers = headers

        async def chat(self, messages, websocket):
            # ensure messages forwarded correctly
            assert isinstance(messages, list)
            # simulate returning response content and tool_calls metadata
            return "response content", [{"tool": "t1"}]

    monkeypatch.setattr(su, 'ChatAgentWithMemory', FakeAgent)

    await su.handle_chat_command(ws, data)

    assert len(ws.sent) == 1
    payload = ws.sent[0]
    assert payload["type"] == "chat"
    assert payload["content"] == "response content"
    assert payload["role"] == "assistant"
    # metadata should be present and wrap the returned tool_calls metadata
    assert payload["metadata"] == {"tool_calls": [{"tool": "t1"}]}


@pytest.mark.asyncio
async def test_success_without_metadata_round_044(monkeypatch):
    """When ChatAgentWithMemory.chat returns response and falsy metadata, the 'metadata' field should be None."""
    ws = FakeWebsocket()
    data = 'chat {"messages": [{"role": "user", "content": "hi"}]}'

    class FakeAgentNoMeta:
        def __init__(self, report, config_path, headers):
            pass

        async def chat(self, messages, websocket):
            return "ok no meta", None

    monkeypatch.setattr(su, 'ChatAgentWithMemory', FakeAgentNoMeta)

    await su.handle_chat_command(ws, data)

    assert len(ws.sent) == 1
    payload = ws.sent[0]
    assert payload["content"] == "ok no meta"
    # metadata should be explicitly None per implementation
    assert payload["metadata"] is None


@pytest.mark.asyncio
async def test_json_decode_error_round_044():
    """Malformed JSON after the 'chat ' prefix should trigger JSONDecodeError handling and send an error message back."""
    ws = FakeWebsocket()
    # Provide invalid JSON that json.loads will raise JSONDecodeError for
    data = 'chat {"incomplete": '

    await su.handle_chat_command(ws, data)

    assert len(ws.sent) == 1
    payload = ws.sent[0]
    assert payload["type"] == "chat"
    assert payload["role"] == "assistant"
    # message should indicate invalid format
    assert "Invalid message format" in payload["content"]


@pytest.mark.asyncio
async def test_chat_exception_round_044(monkeypatch):
    """If the chat agent raises a generic exception during processing, the generic exception handler should send an error message containing the exception text."""
    ws = FakeWebsocket()
    data = 'chat {"messages": [{"role": "user", "content": "trigger"}]}'

    class ExplodingAgent:
        def __init__(self, report, config_path, headers):
            pass

        async def chat(self, messages, websocket):
            raise RuntimeError("boom-boom")

    monkeypatch.setattr(su, 'ChatAgentWithMemory', ExplodingAgent)

    await su.handle_chat_command(ws, data)

    assert len(ws.sent) == 1
    payload = ws.sent[0]
    assert payload["type"] == "chat"
    assert payload["role"] == "assistant"
    assert "Error processing your message" in payload["content"]
    assert "boom-boom" in payload["content"]
