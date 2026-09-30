# file: gpt_researcher/utils/tools.py:230-271
# asked: {"lines": [240, 241, 243, 244, 245, 246, 247, 248, 249, 250, 251, 253, 254, 255, 256, 257, 258, 259, 262, 263, 264, 265, 266, 267, 269, 271], "branches": [[245, 246], [245, 253], [247, 248], [247, 251], [262, 263], [262, 264], [264, 265], [264, 266], [266, 267], [266, 269]]}
# gained: {"lines": [240, 241, 243, 244, 245, 246, 247, 248, 249, 250, 251, 253, 254, 255, 256, 257, 258, 259, 262, 263, 264, 265, 266, 267, 269, 271], "branches": [[245, 246], [245, 253], [247, 248], [247, 251], [262, 263], [262, 264], [264, 265], [264, 266], [266, 267], [266, 269]]}

import asyncio
import inspect
import pytest

from gpt_researcher.utils import tools as tools_module


class DummyLogger:
    def __init__(self):
        self.calls = []

    def error(self, *args, **kwargs):
        self.calls.append((args, kwargs))


def make_results(n):
    return {
        "results": [
            {"title": f"Title {i}", "content": "C" * 400, "url": f"https://example.com/{i}"}
            for i in range(n)
        ]
    }


def _call_tool(tool_obj, arg):
    """
    Helper to call the returned tool object from create_search_tool.
    The @tool decorator may return a StructuredTool-like object that exposes .run or .func.
    This helper tries .run, then .func, then direct call. If the result is awaitable, run it.
    """
    if hasattr(tool_obj, "run") and callable(tool_obj.run):
        result = tool_obj.run(arg)
    elif hasattr(tool_obj, "func") and callable(tool_obj.func):
        result = tool_obj.func(arg)
    elif callable(tool_obj):
        result = tool_obj(arg)
    else:
        raise AssertionError("Tool object is not callable and has no run/func attributes")

    if inspect.isawaitable(result):
        return asyncio.run(result)
    return result


def test_search_tool_with_results_and_truncation(monkeypatch):
    # Ensure logger doesn't produce side effects
    dummy_logger = DummyLogger()
    monkeypatch.setattr(tools_module, "logger", dummy_logger)

    # Create a search_function that returns 6 results (only first 5 should be used)
    def search_fn(query):
        assert query == "my query"
        return make_results(6)

    search_tool = tools_module.create_search_tool(search_fn)
    out = _call_tool(search_tool, "my query")

    # Basic expected header
    assert out.startswith("Search results for 'my query':\n\n")

    # Exactly 5 titles should be present (only first five results are included)
    assert out.count("Title:") == 5

    # Content should be truncated to 300 characters followed by "..."
    assert "Content: " in out
    # Find first content line
    content_lines = [line for line in out.splitlines() if line.startswith("Content: ")]
    assert content_lines, "No content lines found"
    snippet_line = content_lines[0]
    # After "Content: " there should be 300 'C' characters then "..."
    assert snippet_line == "Content: " + ("C" * 300) + "..."

    # URLs should be present for the included results
    assert "URL: https://example.com/0" in out
    assert "URL: https://example.com/4" in out
    # The 6th result (index 5) should NOT be present
    assert "https://example.com/5" not in out

    # logger should not have been called for a successful search
    assert dummy_logger.calls == []


def test_search_tool_no_results_cases(monkeypatch):
    dummy_logger = DummyLogger()
    monkeypatch.setattr(tools_module, "logger", dummy_logger)

    # Case 1: results dict missing 'results' key
    def search_fn_missing(query):
        return {"other": 123}

    search_tool_missing = tools_module.create_search_tool(search_fn_missing)
    out_missing = _call_tool(search_tool_missing, "q1")
    assert out_missing == "No search results found for: q1"

    # Case 2: results present but empty list -> header with no entries
    def search_fn_empty(query):
        return {"results": []}

    search_tool_empty = tools_module.create_search_tool(search_fn_empty)
    out_empty = _call_tool(search_tool_empty, "q2")
    assert out_empty == "Search results for 'q2':\n\n"

    # No logging for these "no results" cases either
    assert dummy_logger.calls == []


@pytest.mark.parametrize(
    "exc_msg, expected",
    [
        ("Invalid API Key provided", "Search failed: API key issue. Please verify your search API credentials are configured correctly."),
        ("The request timed out while connecting", "Search timed out. The search request took too long. Please try again with a different query."),
        ("Rate limit exceeded for this account", "Search rate limit exceeded. Please wait a moment before trying again."),
        ("Unexpected failure: something blew up", "Search encountered an error: Unexpected failure: something blew up. Please check your search provider configuration."),
    ],
)
def test_search_tool_exception_branches(monkeypatch, exc_msg, expected):
    dummy_logger = DummyLogger()
    monkeypatch.setattr(tools_module, "logger", dummy_logger)

    def raising_search_fn(query):
        raise Exception(exc_msg)

    search_tool = tools_module.create_search_tool(raising_search_fn)
    out = _call_tool(search_tool, "q-exc")

    # Ensure return message matches expected branch handling
    assert out == expected

    # Ensure logger.error was called and includes the error type/message
    assert dummy_logger.calls, "logger.error should have been called on exception"
    args, kwargs = dummy_logger.calls[-1]
    # First positional arg should be the formatted message starting with "Search tool error:"
    assert args and isinstance(args[0], str)
    assert args[0].startswith("Search tool error:")
    # exc_info=True should have been passed
    assert kwargs.get("exc_info", False) is True
