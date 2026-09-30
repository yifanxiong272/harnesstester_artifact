# file: gpt_researcher/mcp/tool_selector.py:163-204
# asked: {"lines": [163, 175, 180, 182, 183, 184, 187, 188, 189, 190, 191, 192, 194, 195, 198, 199, 201, 202, 204], "branches": [[182, 183], [182, 198], [188, 189], [188, 194], [189, 190], [189, 191], [191, 188], [191, 192], [194, 182], [194, 195], [201, 202], [201, 204]]}
# gained: {"lines": [163, 175, 180, 182, 183, 184, 187, 188, 189, 190, 191, 192, 194, 195, 198, 199, 201, 202, 204], "branches": [[182, 183], [182, 198], [188, 189], [188, 194], [189, 190], [189, 191], [191, 188], [191, 192], [194, 182], [194, 195], [201, 202], [201, 204]]}

import types
from types import SimpleNamespace

import pytest

from gpt_researcher.mcp import tool_selector as ts_module
from gpt_researcher.mcp.tool_selector import MCPToolSelector


class DummyTool:
    def __init__(self, name, description=None):
        self.name = name
        self.description = description


def test_fallback_selection_picks_top_tools(monkeypatch):
    # Prepare tools with various matches in names and descriptions
    tool_a = DummyTool("SuperSearch", "")
    tool_b = DummyTool("DataFetcher", "Fetches user data and can retrieve records")
    tool_c = DummyTool("Viewer", "View and describe items in the dataset")
    tool_d = DummyTool("Other", "Unrelated functionality")
    tool_e = DummyTool("Misc", "This will search records in archives")  # description-only match

    all_tools = [tool_a, tool_b, tool_c, tool_d, tool_e]

    selector = MCPToolSelector(cfg={})

    # Capture logger.info calls by replacing the module logger with a simple namespace
    logged = []
    def fake_info(msg):
        logged.append(msg)

    fake_logger = SimpleNamespace(info=fake_info)
    monkeypatch.setattr(ts_module, "logger", fake_logger)

    # Select top 3 tools
    selected = selector._fallback_tool_selection(all_tools, max_tools=3)

    # Expected scores:
    # tool_b: 5 (3 for 'fetch' in name, +1 for 'fetch' in desc, +1 for 'retrieve' in desc)
    # tool_c: 5 (3 for 'view' in name, +1 for 'view' in desc, +1 for 'describe' in desc)
    # tool_a: 3 (3 for 'search' in name)
    # Because sort is stable, tool_b (earlier in all_tools) will come before tool_c when tied.
    assert [t.name for t in selected] == ["DataFetcher", "Viewer", "SuperSearch"]

    # Verify logger.info was called for each selected tool with expected formatting and contents
    assert len(logged) == 3
    assert logged[0] == "Fallback selected tool 1: DataFetcher (score: 5)"
    assert logged[1] == "Fallback selected tool 2: Viewer (score: 5)"
    assert logged[2] == "Fallback selected tool 3: SuperSearch (score: 3)"

    # Ensure no tool with zero score was selected
    assert "Other" not in [t.name for t in selected]


def test_fallback_selection_no_matches_returns_empty_and_no_logging(monkeypatch):
    # Tools with no matching patterns
    tool1 = DummyTool("Alpha", "completely unrelated")
    tool2 = DummyTool("Beta", None)
    all_tools = [tool1, tool2]

    selector = MCPToolSelector(cfg={})

    # Replace logger to ensure no info calls are made
    logged = []
    fake_logger = SimpleNamespace(info=lambda msg: logged.append(msg))
    monkeypatch.setattr(ts_module, "logger", fake_logger)

    selected = selector._fallback_tool_selection(all_tools, max_tools=5)

    # No tools should be selected since none match the patterns
    assert selected == []
    # Logger should not have been called
    assert logged == []
