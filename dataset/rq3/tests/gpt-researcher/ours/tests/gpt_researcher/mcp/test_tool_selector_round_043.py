import logging
from gpt_researcher.mcp.tool_selector import MCPToolSelector


class ToolStub:
    def __init__(self, name, description=None):
        self.name = name
        self.description = description


def test_name_and_description_scoring_round_043(caplog):
    """Verify that name and description matches accumulate scores and that
    the top-N tools are returned in the expected order. Also assert logging.
    """
    selector = MCPToolSelector(cfg=None)

    # Create tools with name and description matches
    t_web = ToolStub("WebSearch", "Use to search web")      # name contains 'search', desc contains 'search' -> 4
    t_fetch = ToolStub("Fetcher", "Fetch data from API")   # name contains 'fetch', desc contains 'fetch' -> 4
    t_list = ToolStub("ListTool", "List available items")  # name contains 'list', desc contains 'list' -> 4
    t_other = ToolStub("Other", "No relevant keywords")    # score 0 -> should be excluded

    all_tools = [t_web, t_fetch, t_list, t_other]

    caplog.set_level(logging.INFO)
    selected = selector._fallback_tool_selection(all_tools, max_tools=2)

    # Expect first two tools in original order among the highest-scoring tools
    assert [t.name for t in selected] == ["WebSearch", "Fetcher"]

    # Check that logging recorded the selected tools and their scores
    info_msgs = [rec.getMessage() for rec in caplog.records if "Fallback selected tool" in rec.getMessage()]
    assert any("Fallback selected tool 1: WebSearch (score: 4)" == m for m in info_msgs)
    assert any("Fallback selected tool 2: Fetcher (score: 4)" == m for m in info_msgs)


def test_description_only_and_sorting_round_043(caplog):
    """Verify description-only matches yield lower scores than name matches,
    multiple description matches accumulate, and returned order is sorted by score.
    """
    selector = MCPToolSelector(cfg=None)

    # Name match (higher weight)
    t_name = ToolStub("SearcherName", "no relevant desc")  # name contains 'search' -> +3

    # Description-only matches: two different patterns -> +2
    t_desc_multi = ToolStub("ToolB", "can retrieve and list resources")

    # Description-only single match -> +1
    t_desc_single = ToolStub("ToolC", "find resources quickly")

    # No matches -> excluded
    t_none = ToolStub("ToolD", "unrelated")

    all_tools = [t_name, t_desc_multi, t_desc_single, t_none]

    caplog.set_level(logging.INFO)
    selected = selector._fallback_tool_selection(all_tools, max_tools=5)

    # Expect ordering by score: name match (3), desc_multi (2), desc_single (1)
    assert [t.name for t in selected] == ["SearcherName", "ToolB", "ToolC"]

    # Check logging contains entries for each selected tool with proper scores
    info_msgs = [rec.getMessage() for rec in caplog.records if rec.getMessage().startswith("Fallback selected tool")]
    assert any("Fallback selected tool 1: SearcherName (score: 3)" == m for m in info_msgs)
    assert any("Fallback selected tool 2: ToolB (score: 2)" == m for m in info_msgs)
    assert any("Fallback selected tool 3: ToolC (score: 1)" == m for m in info_msgs)
