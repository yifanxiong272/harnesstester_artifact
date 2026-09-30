import importlib
import os
import types
import pytest

import backend.chat.chat as chat_mod
from backend.chat.chat import ChatAgentWithMemory

class DummyConfig:
    def __init__(self, path="default"):
        self.path = path


class DummyLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, msg):
        # Mirror the real logger.warning signature
        self.warnings.append(msg)


class RecordingTavilyClient:
    def __init__(self, api_key=None):
        # record the explicit kwarg to ensure the code passes api_key
        self.api_key = api_key


def _patch_common(monkeypatch, tavily_client=None, logger=None, config=None):
    # Patch attributes on the module where ChatAgentWithMemory resolves symbols
    if tavily_client is not None:
        monkeypatch.setattr(chat_mod, "TavilyClient", tavily_client, raising=True)
    if logger is not None:
        monkeypatch.setattr(chat_mod, "logger", logger, raising=True)
    if config is not None:
        monkeypatch.setattr(chat_mod, "Config", config, raising=True)


def test_tavily_client_created_round_096(monkeypatch):
    """
    When TAVILY_API_KEY is set, __init__ should create a TavilyClient instance
    passing the API key. Also, logger.warning should not be called.
    Covers branch: backend/chat/chat.py:72->73 (True branch creating client).
    """
    # Arrange: ensure environment variable is present
    monkeypatch.setenv("TAVILY_API_KEY", "test-key-123")

    # Prepare and patch a recording TavilyClient and dummy Config/logger
    dummy_logger = DummyLogger()
    _patch_common(
        monkeypatch,
        tavily_client=RecordingTavilyClient,
        logger=dummy_logger,
        config=DummyConfig,
    )

    # Act: instantiate
    agent = ChatAgentWithMemory(report="some-report")

    # Assert: tavily_client was created and received the exact api_key
    assert agent.tavily_client is not None and isinstance(agent.tavily_client, RecordingTavilyClient)
    assert getattr(agent.tavily_client, "api_key") == "test-key-123"

    # Logger warning must not have been called in this branch
    assert dummy_logger.warnings == []


def test_tavily_client_not_set_round_096(monkeypatch):
    """
    When TAVILY_API_KEY is not set, __init__ should set tavily_client to None
    and call logger.warning with the expected message.
    Covers branch: backend/chat/chat.py:72->73 (False branch setting None and warning).
    """
    # Arrange: ensure environment variable is not present
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    # Prepare a TavilyClient that would raise if called (to ensure it's not used)
    class FailIfCalledTavilyClient:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("TavilyClient must not be instantiated when no API key is set")

    dummy_logger = DummyLogger()
    _patch_common(
        monkeypatch,
        tavily_client=FailIfCalledTavilyClient,
        logger=dummy_logger,
        config=DummyConfig,
    )

    # Act: instantiate
    agent = ChatAgentWithMemory(report="another-report")

    # Assert: tavily_client is None and the exact warning message was emitted
    assert agent.tavily_client is None

    expected_msg = "TAVILY_API_KEY not set - web search in chat will be disabled"
    assert dummy_logger.warnings == [expected_msg]
