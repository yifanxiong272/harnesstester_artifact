# file: backend/chat/chat.py:187-254
# asked: {"lines": [197, 200, 214, 216, 221, 224, 225, 226, 230, 231, 232, 233, 234, 237, 240, 243, 244, 245, 247, 250, 252, 253, 254], "branches": [[230, 231], [230, 240], [231, 232], [231, 237], [243, 244], [243, 247]]}
# gained: {"lines": [197, 200, 214, 216, 221, 224, 225, 226, 230, 231, 232, 233, 234, 237, 240, 243, 244, 245, 247, 250, 252, 253, 254], "branches": [[230, 231], [230, 240], [231, 232], [231, 237], [243, 244]]}

import asyncio
import importlib.util
import logging
from pathlib import Path

import pytest

pytestmark = pytest.mark.asyncio


def _locate_and_load_chat_class():
    """
    Search the repository for a file containing ChatAgentWithMemory, load it as a module,
    and return the ChatAgentWithMemory class.
    """
    cwd = Path.cwd()
    candidates = list(cwd.rglob("chat.py"))
    target_file = None
    for p in candidates:
        try:
            text = p.read_text(encoding="utf8")
        except Exception:
            continue
        if "class ChatAgentWithMemory" in text or "ChatAgentWithMemory" in text:
            target_file = p
            break

    if target_file is None:
        pytest.skip("Could not find chat.py defining ChatAgentWithMemory in repository")

    spec = importlib.util.spec_from_file_location(f"test_chat_module_{abs(hash(str(target_file))) % (10**8)}", str(target_file))
    module = importlib.util.module_from_spec(spec)
    loader = spec.loader
    if loader is None:
        pytest.skip(f"Could not load module from {target_file}")
    loader.exec_module(module)

    if not hasattr(module, "ChatAgentWithMemory"):
        pytest.skip(f"Module {target_file} does not define ChatAgentWithMemory")
    return module.ChatAgentWithMemory


@pytest.mark.asyncio
async def test_chat_empty_response_triggers_fallback(monkeypatch, caplog):
    ChatAgentWithMemory = _locate_and_load_chat_class()

    caplog.set_level(logging.WARNING)

    # Create instance without calling __init__ in case it requires args
    agent = ChatAgentWithMemory.__new__(ChatAgentWithMemory)
    # Provide minimal state expected by the method
    agent.report = "Sample Report"

    captured = {}

    async def fake_process_chat_completion(formatted_messages):
        # capture the formatted messages passed in
        captured["formatted"] = formatted_messages
        # Return empty AI message to trigger fallback branch and metadata
        return "", {"tool_used": False}

    # Attach our fake async processor to the instance
    # Use monkeypatch.setattr to ensure cleanup after test
    monkeypatch.setattr(agent, "process_chat_completion", fake_process_chat_completion, raising=False)

    # Provide messages where one is missing 'content' to trigger skipping warning
    messages = [
        {"role": "user", "content": "Hello there"},
        {"role": "user"},  # missing content -> should be skipped and logged
    ]

    ai_message, metadata = await agent.chat(messages, websocket=None)

    # Verify fallback was used
    assert ai_message.startswith("I apologize, but I couldn't generate a proper response")
    assert metadata == {"tool_used": False}

    # Verify the formatted messages passed to process_chat_completion
    assert "formatted" in captured
    formatted = captured["formatted"]
    assert isinstance(formatted, list)
    # First message should be the system message containing the report
    assert formatted[0]["role"] == "system"
    assert "Report: Sample Report" in formatted[0]["content"]
    # The user message should be present, the bad one skipped
    assert any(m for m in formatted if m.get("role") == "user" and m.get("content") == "Hello there")
    # Ensure no user message with missing content made it through
    assert not any(m for m in formatted if m.get("role") == "user" and ("content" not in m or m.get("content") is None))

    # Check logs for skipping and fallback warnings
    assert "Skipping message with missing role or content" in caplog.text
    assert "No AI message content found in response, using fallback message" in caplog.text


@pytest.mark.asyncio
async def test_chat_process_raises_logs_and_raises(monkeypatch, caplog):
    ChatAgentWithMemory = _locate_and_load_chat_class()

    caplog.set_level(logging.ERROR)

    # Create instance without __init__
    agent = ChatAgentWithMemory.__new__(ChatAgentWithMemory)
    agent.report = "ErrReport"

    async def fake_raise(formatted_messages):
        raise ValueError("boom")

    monkeypatch.setattr(agent, "process_chat_completion", fake_raise, raising=False)

    with pytest.raises(ValueError) as excinfo:
        await agent.chat([{"role": "user", "content": "trigger error"}])

    # Ensure the exception propagated
    assert "boom" in str(excinfo.value)
    # Ensure an error was logged containing the message
    assert "Error in chat: boom" in caplog.text
