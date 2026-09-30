import os
import pytest
from gpt_researcher.retrievers.tavily.tavily_search import TavilySearch


def test_get_api_key_from_headers_round_141():
    """When headers contain a truthy 'tavily_api_key', get_api_key should return it and not consult the environment."""
    headers = {"tavily_api_key": "header-key-123"}
    ts = TavilySearch("some query", headers=headers)

    # api_key should be taken from supplied headers during __init__
    assert ts.api_key == "header-key-123"


def test_get_api_key_from_env_round_141(monkeypatch):
    """When headers do not provide a key, get_api_key should read TAVILY_API_KEY from the environment."""
    # Ensure environment is controlled deterministically
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("TAVILY_API_KEY", "env-key-xyz")

    # No headers passed => headers starts as {} inside __init__, triggering env lookup
    ts = TavilySearch("q-without-header", headers=None)

    assert ts.api_key == "env-key-xyz"


def test_get_api_key_missing_round_141(monkeypatch, capsys):
    """When neither headers nor environment provide a key, get_api_key should print a message and return an empty string."""
    # Ensure environment variable is absent
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    # No headers provided -> will attempt to read env and fail
    ts = TavilySearch("q-missing", headers=None)

    captured = capsys.readouterr()
    # Should set api_key to empty string when missing and print warning
    assert ts.api_key == ""
    assert "Tavily API key not found" in captured.out
