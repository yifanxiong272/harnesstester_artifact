import asyncio
import json
import pytest

from backend.server import server_utils


class DummyWebSocketRound_044:
    def __init__(self):
        self.sent = []

    async def send_json(self, data):
        # store a deep-copiable representation for assertions
        self.sent.append(data)


@pytest.mark.asyncio
async def test_message_only_to_unavailable_agent_round_044(monkeypatch):
    """If only 'message' is provided and ChatAgentWithMemory is None, the code
    should convert message -> messages and then inform the client that chat
    functionality is not available."""
    # ensure ChatAgentWithMemory is unavailable
    monkeypatch.setattr(server_utils, "ChatAgentWithMemory", None)

    ws = DummyWebSocketRound_044()
    message = "hello there"
    payload = {"message": message}
    data = "chat " + json.dumps(payload)

    await server_utils.handle_chat_command(ws, data)

    assert len(ws.sent) == 1
    sent = ws.sent[0]
    assert sent["type"] == "chat"
    assert "Chat functionality is not available" in sent["content"]
    assert sent["role"] == "assistant"


@pytest.mark.asyncio
async def test_no_message_round_044(monkeypatch):
    """If neither 'message' nor 'messages' are provided, the handler should
    reply with 'No message provided.'"""
    # make sure ChatAgentWithMemory is irrelevant for this branch
    monkeypatch.setattr(server_utils, "ChatAgentWithMemory", object)

    ws = DummyWebSocketRound_044()
    data = "chat " + json.dumps({})

    await server_utils.handle_chat_command(ws, data)

    assert len(ws.sent) == 1
    sent = ws.sent[0]
    assert sent["type"] == "chat"
    assert sent["content"] == "No message provided."
    assert sent["role"] == "assistant"


@pytest.mark.asyncio
async def test_agent_success_with_no_tools_round_044(monkeypatch):
    """When a ChatAgentWithMemory is present and returns no tool_calls (falsy),
    metadata in the outgoing message should be None."""

    class DummyAgentRound_044:
        def __init__(self, report, config_path, headers):
            self.report = report
            self.config_path = config_path
            self.headers = headers

        async def chat(self, messages, websocket):
            # Return a content and falsy tool_calls_metadata to exercise metadata -> None
            return "assistant reply", None

    monkeypatch.setattr(server_utils, "ChatAgentWithMemory", DummyAgentRound_044)

    ws = DummyWebSocketRound_044()
    messages = [{"role": "user", "content": "ping"}]
    data = "chat " + json.dumps({"messages": messages})

    await server_utils.handle_chat_command(ws, data)

    assert len(ws.sent) == 1
    sent = ws.sent[0]
    assert sent["type"] == "chat"
    assert sent["content"] == "assistant reply"
    # metadata should be exactly None when tool_calls_metadata is falsy
    assert sent.get("metadata") is None


@pytest.mark.asyncio
async def test_agent_success_with_tools_round_044(monkeypatch):
    """When ChatAgentWithMemory.chat returns tool call metadata (truthy), the
    outgoing message should include a metadata dict with that tool_calls list."""

    class DummyAgentWithToolsRound_044:
        def __init__(self, report, config_path, headers):
            pass

        async def chat(self, messages, websocket):
            return "with tools", [{"tool": "t1"}]

    monkeypatch.setattr(server_utils, "ChatAgentWithMemory", DummyAgentWithToolsRound_044)

    ws = DummyWebSocketRound_044()
    data = "chat " + json.dumps({"messages": [{"role": "user", "content": "do something"}]})

    await server_utils.handle_chat_command(ws, data)

    assert len(ws.sent) == 1
    sent = ws.sent[0]
    assert sent["type"] == "chat"
    assert sent["content"] == "with tools"
    assert isinstance(sent.get("metadata"), dict)
    assert sent["metadata"]["tool_calls"] == [{"tool": "t1"}]


@pytest.mark.asyncio
async def test_invalid_json_round_044():
    """Invalid JSON after the 'chat ' prefix should be caught and an error
    message sent describing invalid format."""
    ws = DummyWebSocketRound_044()
    # malformed JSON
    data = "chat {not: valid json}"

    await server_utils.handle_chat_command(ws, data)

    assert len(ws.sent) == 1
    sent = ws.sent[0]
    assert sent["type"] == "chat"
    # exact JSONDecodeError message can vary, assert the handler produced the expected prefix
    assert sent["content"].startswith("Error: Invalid message format")
    assert sent["role"] == "assistant"


@pytest.mark.asyncio
async def test_agent_chat_raises_round_044(monkeypatch):
    """If the chat agent raises a generic exception, the handler should
    catch it and respond with an error-processing message containing the
    exception text."""

    class BrokenAgentRound_044:
        def __init__(self, report, config_path, headers):
            pass

        async def chat(self, messages, websocket):
            raise RuntimeError("boom")

    monkeypatch.setattr(server_utils, "ChatAgentWithMemory", BrokenAgentRound_044)

    ws = DummyWebSocketRound_044()
    data = "chat " + json.dumps({"messages": [{"role": "user", "content": "trigger"}]})

    await server_utils.handle_chat_command(ws, data)

    assert len(ws.sent) == 1
    sent = ws.sent[0]
    assert sent["type"] == "chat"
    assert "Error processing your message" in sent["content"]
    assert "boom" in sent["content"]
    assert sent["role"] == "assistant"
