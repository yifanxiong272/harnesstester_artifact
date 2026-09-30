# file: backend/chat/chat.py:114-150
# asked: {"lines": [116, 118, 119, 120, 121, 122, 123, 125, 126, 127, 130, 131, 134, 135, 136, 137, 138, 139, 140, 144, 145, 146, 147, 148, 149], "branches": [[118, 119], [118, 130]]}
# gained: {"lines": [116, 118, 119, 120, 121, 122, 123, 125, 126, 127, 130, 131, 134, 135, 136, 137, 138, 139, 140, 144, 145, 146, 147, 148, 149], "branches": [[118, 119], [118, 130]]}

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_chat_class():
    """
    Dynamically locate and load the module that defines ChatAgentWithMemory.
    Searches the current working directory recursively for a chat.py that contains
    the class definition, then imports it as a module and returns the class.
    """
    cwd = Path.cwd()
    candidates = list(cwd.rglob("chat.py"))
    for p in candidates:
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if "class ChatAgentWithMemory" in text:
            spec = importlib.util.spec_from_file_location("chat_module_for_test", p)
            mod = importlib.util.module_from_spec(spec)
            loader = spec.loader
            assert loader is not None
            loader.exec_module(mod)
            if hasattr(mod, "ChatAgentWithMemory"):
                return mod.ChatAgentWithMemory
    # Fallback: try common package path if present on sys.path
    try:
        mod = importlib.import_module("gpt_researcher.backend.chat.chat")
        return getattr(mod, "ChatAgentWithMemory")
    except Exception:
        pass
    raise RuntimeError("Could not find ChatAgentWithMemory class in repository")


ChatAgentWithMemory = _load_chat_class()


def make_agent():
    """
    Create a ChatAgentWithMemory instance without invoking its __init__,
    to avoid side-effects and required constructor arguments.
    """
    agent = object.__new__(ChatAgentWithMemory)
    # Ensure no leftover attributes
    if hasattr(agent, "search_metadata"):
        delattr(agent, "search_metadata")
    return agent


def test_quick_search_with_no_tavily_client_sets_metadata_and_returns_error():
    agent = make_agent()
    agent.tavily_client = None

    result = agent.quick_search("test query")

    assert isinstance(result, dict)
    assert result["error"] == "Web search is disabled - TAVILY_API_KEY not configured"
    assert result["results"] == []

    # search_metadata should be set on the agent with expected structure
    assert hasattr(agent, "search_metadata")
    meta = agent.search_metadata
    assert meta["query"] == "test query"
    assert meta["sources"] == []
    assert "Web search is disabled" in meta["error"]


def test_quick_search_with_tavily_client_returns_results_and_truncates_content():
    agent = make_agent()

    # Prepare results with one long content (>200 chars) and one short
    long_content = "x" * 300
    short_content = "short content"
    results_dict = {
        "results": [
            {"title": "LongTitle", "url": "http://long", "content": long_content},
            {"title": "ShortTitle", "url": "http://short", "content": short_content},
        ]
    }

    class DummyClient:
        def search(self, query, max_results):
            # verify parameters passed through as expected
            assert query == "some query"
            assert max_results == 5
            return results_dict

    agent.tavily_client = DummyClient()

    returned = agent.quick_search("some query")

    # Should return the raw results dict from the client
    assert returned is results_dict

    # search_metadata should exist and have truncated content for long item
    assert hasattr(agent, "search_metadata")
    meta = agent.search_metadata
    assert meta["query"] == "some query"
    sources = meta["sources"]
    assert len(sources) == 2

    # First item: content truncated to 200 chars + "..."
    expected_truncated = long_content[:200] + "..."
    assert sources[0]["title"] == "LongTitle"
    assert sources[0]["url"] == "http://long"
    assert sources[0]["content"] == expected_truncated

    # Second item unchanged
    assert sources[1]["title"] == "ShortTitle"
    assert sources[1]["url"] == "http://short"
    assert sources[1]["content"] == short_content


def test_quick_search_handles_exceptions_and_returns_error_dict():
    agent = make_agent()

    class ExplodingClient:
        def search(self, query, max_results):
            raise RuntimeError("boom")

    agent.tavily_client = ExplodingClient()

    result = agent.quick_search("will fail")

    assert isinstance(result, dict)
    # should report the exception message and return empty results list
    assert result["error"] == "boom"
    assert result["results"] == []

    # If search_metadata existed before, it should remain unchanged; otherwise it should not be created
    if hasattr(agent, "search_metadata"):
        assert isinstance(agent.search_metadata, dict)
