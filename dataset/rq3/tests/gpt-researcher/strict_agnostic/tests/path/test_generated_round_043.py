import pytest
from gpt_researcher.mcp import tool_selector as ts


class Tool:
    """Simple stand-in for tool objects expected by MCPToolSelector._fallback_tool_selection."""
    def __init__(self, name, description=None):
        self.name = name
        self.description = description


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, msg):
        # store messages for assertions
        self.messages.append(msg)


def _make_selector_instance():
    # Bypass __init__ to avoid needing real cfg/researcher; we only need the method under test.
    return object.__new__(ts.MCPToolSelector)


def test_single_tool_name_round_043(monkeypatch):
    """Tool name contains a research pattern -> score from name applied; description None handled."""
    selector = _make_selector_instance()
    logger = DummyLogger()
    monkeypatch.setattr(ts, "logger", logger)

    web_search = Tool("WebSearch", None)

    selected = selector._fallback_tool_selection([web_search], max_tools=1)

    # The tool name contains 'search' -> score should be 3 and the tool should be selected.
    assert selected == [web_search]

    # The function logs info for each selected tool. Validate logging happened and includes score and name.
    assert len(logger.messages) == 1
    assert "WebSearch" in logger.messages[0]
    assert "(score: 3)" in logger.messages[0]


def test_multiple_tools_sorting_and_description_round_043(monkeypatch):
    """Multiple tools with different name/description matches -> sorted by score and top N returned."""
    selector = _make_selector_instance()
    logger = DummyLogger()
    monkeypatch.setattr(ts, "logger", logger)

    # t1: name contains 'search' (3) and description contains 'list' (1) => score 4
    t1 = Tool("Searcher", "Provides list of results")
    # t2: name contains 'read' (3), description None => score 3
    t2 = Tool("Reader", None)
    # t3: name doesn't contain patterns, description contains 'query' => score 1
    t3 = Tool("QTool", "Can query database")
    # t4: no matching patterns => score 0 and should be excluded
    t4 = Tool("Compute", "Performs math")

    # Provide tools out of score order to ensure sorting is exercised
    all_tools = [t3, t2, t4, t1]

    selected = selector._fallback_tool_selection(all_tools, max_tools=2)

    # Expect top two by score: t1 (4), then t2 (3)
    assert selected == [t1, t2]

    # Two selections should produce two log lines; verify content and order/score info
    assert len(logger.messages) == 2
    assert "Fallback selected tool 1:" in logger.messages[0]
    assert "Searcher" in logger.messages[0]
    assert "(score: 4)" in logger.messages[0]
    assert "Fallback selected tool 2:" in logger.messages[1]
    assert "Reader" in logger.messages[1]
    assert "(score: 3)" in logger.messages[1]
