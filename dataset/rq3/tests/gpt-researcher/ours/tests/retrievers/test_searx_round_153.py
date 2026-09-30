import os
import pytest
from gpt_researcher.retrievers.searx.searx import SearxSearch


def test_get_searxng_url_with_trailing_slash_round_153(monkeypatch):
    # If SEARX_URL already ends with '/', it should be returned unchanged
    monkeypatch.setenv("SEARX_URL", "https://example.com/")
    result = SearxSearch.get_searxng_url(object())
    assert result == "https://example.com/"


def test_get_searxng_url_without_trailing_slash_round_153(monkeypatch):
    # If SEARX_URL does not end with '/', it should append one
    monkeypatch.setenv("SEARX_URL", "https://example.org")
    result = SearxSearch.get_searxng_url(object())
    assert result == "https://example.org/"


def test_get_searxng_url_missing_env_round_153(monkeypatch):
    # If SEARX_URL is not set, an Exception with a helpful message should be raised
    monkeypatch.delenv("SEARX_URL", raising=False)
    with pytest.raises(Exception) as excinfo:
        SearxSearch.get_searxng_url(object())
    message = str(excinfo.value)
    assert "SearxNG URL not found" in message
    # Ensure guidance URL is present in the message
    assert "https://searx.space/" in message
