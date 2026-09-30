import pytest

from gpt_researcher.skills.researcher import ResearchConductor


class LoggerCapture:
    def __init__(self):
        self.debug_msgs = []
        self.info_msgs = []
        self.warning_msgs = []

    def debug(self, *args, **kwargs):
        self.debug_msgs.append(" ".join(str(a) for a in args))

    def info(self, *args, **kwargs):
        self.info_msgs.append(" ".join(str(a) for a in args))

    def warning(self, *args, **kwargs):
        self.warning_msgs.append(" ".join(str(a) for a in args))


class DummySelf:
    def __init__(self):
        self.logger = LoggerCapture()


def test_with_web_and_mcp_entries_round_029():
    """Web context present and multiple MCP items with different URL cases.

    This exercises the branch where web_context is added, multiple MCP entries are
    formatted, one with a normal URL (should include URL in citation) and one with
    the special mcp://llm_analysis URL (should omit URL from citation).
    """
    dummy = DummySelf()

    web_context = "  Web summary here.  "

    mcp_context = [
        {"content": "First content.", "url": "http://example.com", "title": "Example"},
        # omit the 'title' key to trigger the default title behavior in the implementation
        {"content": "Second content", "url": "mcp://llm_analysis"},
    ]

    result = ResearchConductor._combine_mcp_and_web_context(
        dummy, mcp_context, web_context, "query1"
    )

    # web context should be present and stripped
    assert "Web summary here." in result

    # first MCP entry should include the URL in the citation
    assert "*Source: Example (http://example.com)*" in result

    # second MCP entry should use default title for the second entry (index 1 -> MCP Result 2)
    assert "*Source: MCP Result 2*" in result

    # MCP entries should be separated by the '---' section marker
    assert "---" in result

    # info log should report combined context for the provided sub_query
    assert any("Combined context for 'query1'" in m for m in dummy.logger.info_msgs)


def test_with_empty_web_and_no_valid_mcp_round_029():
    """Whitespace web context and MCP entries without usable content should return empty string.

    This exercises the branches where web_context is treated as absent (only whitespace)
    and MCP items have empty content so nothing gets appended -> final empty return and warning.
    """
    dummy = DummySelf()

    web_context = "   "  # whitespace only

    mcp_context = [
        {"content": "", "url": "http://example.com", "title": "T1"},
        {"content": "   ", "url": "", "title": "T2"},
    ]

    result = ResearchConductor._combine_mcp_and_web_context(
        dummy, mcp_context, web_context, "test2"
    )

    # No usable content from web or MCP -> empty string
    assert result == ""

    # warning log should mention no context to combine for the sub-query
    assert any("No context to combine for sub-query: test2" in m for m in dummy.logger.warning_msgs)


def test_mcp_only_round_029():
    """No web_context provided, a single MCP item creates an MCP-only combined context.

    This exercises the branch where web_context is falsy but valid MCP content exists.
    It also verifies citation formatting when url is empty (should not include a URL).
    """
    dummy = DummySelf()

    web_context = None

    mcp_context = [
        {"content": "Only content here.", "url": "", "title": "My Title"}
    ]

    result = ResearchConductor._combine_mcp_and_web_context(
        dummy, mcp_context, web_context, "just mcp"
    )

    # ensure the MCP content is present
    assert "Only content here." in result

    # citation should include title but no URL
    assert "*Source: My Title*" in result

    # debug should report that MCP context entries were added (len == 1)
    assert any("Added 1 MCP context entries" in m for m in dummy.logger.debug_msgs)
