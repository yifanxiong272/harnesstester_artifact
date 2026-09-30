import types
import logging
import pytest
from datetime import datetime as real_datetime

import backend.chat.chat as chat_mod
from backend.chat.chat import ChatAgentWithMemory

FALLBACK_MSG = "I apologize, but I couldn't generate a proper response. Please try asking your question again."

class FakeDatetime:
    @staticmethod
    def now():
        # deterministic timestamp for predictable system prompt
        return real_datetime(2020, 1, 1, 0, 0, 0)

@pytest.mark.asyncio
async def test_chat_success_round_058(caplog, monkeypatch):
    """
    - Ensure system message is added
    - Ensure messages missing role/content are skipped (warning logged)
    - Ensure non-empty ai_message from provider is returned unchanged
    """
    caplog.set_level(logging.INFO)
    # Patch datetime in the module to deterministic FakeDatetime
    monkeypatch.setattr(chat_mod, "datetime", FakeDatetime)

    captured = {}

    async def fake_process_chat_completion(formatted_messages):
        # capture the formatted messages for assertions
        captured['formatted'] = formatted_messages
        return "Hello from AI", {"tools": []}

    # Create a lightweight dummy instance to avoid running __init__
    dummy = types.SimpleNamespace(report="REPORT-XYZ", process_chat_completion=fake_process_chat_completion)

    # Provide one valid message and one invalid to trigger the skipping branch
    messages = [
        {"role": "user", "content": "What is the report about?"},
        {"content_only": "missing role field"}
    ]

    ai_message, metadata = await ChatAgentWithMemory.chat(dummy, messages)

    # Assertions about returned values
    assert ai_message == "Hello from AI"
    assert metadata == {"tools": []}

    # Assertions about formatted messages structure passed to provider
    fm = captured.get('formatted')
    assert fm is not None
    # first message must be the system prompt
    assert isinstance(fm, list)
    assert fm[0]["role"] == "system"
    # the valid user message should be appended
    assert any(m.get("role") == "user" and m.get("content") == "What is the report about?" for m in fm)
    # the invalid message should have been skipped; check for logged warning
    assert any("Skipping message with missing role or content" in rec.message for rec in caplog.records)
    # an info log for generated response should exist
    assert any("Generated response" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_chat_fallback_empty_ai_round_058(caplog, monkeypatch):
    """
    - If process_chat_completion returns an empty ai_message, the fallback string is used
    - The fallback warning is logged
    """
    caplog.set_level(logging.WARNING)
    monkeypatch.setattr(chat_mod, "datetime", FakeDatetime)

    async def fake_empty_ai(formatted_messages):
        return "", {"meta": 1}

    dummy = types.SimpleNamespace(report="REPORT-XYZ", process_chat_completion=fake_empty_ai)

    messages = [{"role": "user", "content": "Say something."}]

    ai_message, metadata = await ChatAgentWithMemory.chat(dummy, messages)

    assert ai_message == FALLBACK_MSG
    assert metadata == {"meta": 1}
    # ensure fallback warning logged
    assert any("No AI message content found in response, using fallback message" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_chat_raises_round_058(caplog, monkeypatch):
    """
    - If an exception occurs during processing, it should be logged and re-raised
    - This covers the except branch
    """
    caplog.set_level(logging.ERROR)
    monkeypatch.setattr(chat_mod, "datetime", FakeDatetime)

    async def fake_raises(formatted_messages):
        raise RuntimeError("boom")

    dummy = types.SimpleNamespace(report="REPORT-XYZ", process_chat_completion=fake_raises)

    messages = [{"role": "user", "content": "Trigger error."}]

    with pytest.raises(RuntimeError) as excinfo:
        await ChatAgentWithMemory.chat(dummy, messages)

    assert "boom" in str(excinfo.value)
    # ensure error was logged with the message
    assert any("Error in chat: boom" in rec.message for rec in caplog.records)
