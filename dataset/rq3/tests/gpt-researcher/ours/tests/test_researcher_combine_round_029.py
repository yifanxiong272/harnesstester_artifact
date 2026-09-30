import pytest

from gpt_researcher.skills.researcher import ResearchConductor


class DummyLogger:
    def __init__(self):
        self.debug_msgs = []
        self.info_msgs = []
        self.warn_msgs = []

    def debug(self, msg):
        self.debug_msgs.append(msg)

    def info(self, msg):
        self.info_msgs.append(msg)

    def warning(self, msg):
        self.warn_msgs.append(msg)


class DummySelf:
    def __init__(self):
        self.logger = DummyLogger()


def test_combine_with_web_and_mcp_round_029():
    # Arrange
    dummy = DummySelf()
    web_context = "  Web context here  "
    mcp_context = [
        {"content": "  Content A  ", "url": "http://example.com", "title": "Title A"},
        {"content": "Content B", "url": "mcp://llm_analysis"},  # missing title -> default
        {"content": "   ", "url": "http://skipped.example", "title": "Should be skipped"},
    ]
    sub_query = "my-sub-query"

    # Act
    result = ResearchConductor._combine_mcp_and_web_context(dummy, mcp_context, web_context, sub_query)

    # Build expected pieces exactly as the function does
    formatted0 = "Content A" + "\n\n*Source: Title A (http://example.com)*"
    formatted1 = "Content B" + "\n\n*Source: MCP Result 2*"
    mcp_section = formatted0 + "\n\n---\n\n" + formatted1
    expected = web_context.strip() + "\n\n" + mcp_section

    # Assert return value
    assert result == expected

    # Assert logger messages: debug for web context used original web_context length
    assert any(msg == f"Added web context: {len(web_context)} chars" for msg in dummy.logger.debug_msgs)

    # It logs number of MCP context entries (len of provided mcp_context)
    assert any(msg == f"Added {len(mcp_context)} MCP context entries" for msg in dummy.logger.debug_msgs)

    # It logs an info message with the combined length
    expected_info = f"Combined context for '{sub_query}': {len(expected)} total chars"
    assert dummy.logger.info_msgs and dummy.logger.info_msgs[-1] == expected_info


def test_combine_only_mcp_no_web_round_029():
    # Arrange
    dummy = DummySelf()
    web_context = "   "  # whitespace only -> should be ignored
    mcp_context = [
        {"content": "First content", "url": ""},  # missing url -> treated as special (empty -> citation without URL)
        {"content": "   ", "url": "http://skip.example"},  # whitespace content -> skipped entirely
    ]
    sub_query = "only-mcp"

    # Act
    result = ResearchConductor._combine_mcp_and_web_context(dummy, mcp_context, web_context, sub_query)

    # Expect only the first MCP entry formatted, title defaults to MCP Result 1
    formatted0 = "First content" + "\n\n*Source: MCP Result 1*"
    expected = formatted0

    # Assert return value
    assert result == expected

    # Since web_context is whitespace, no web debug message should be present
    assert not any(msg.startswith("Added web context:") for msg in dummy.logger.debug_msgs)

    # The function logs the number of MCP context entries (len provided), because mcp_formatted is non-empty
    assert any(msg == f"Added {len(mcp_context)} MCP context entries" for msg in dummy.logger.debug_msgs)

    # Info log should reflect the combined length
    expected_info = f"Combined context for '{sub_query}': {len(expected)} total chars"
    assert dummy.logger.info_msgs and dummy.logger.info_msgs[-1] == expected_info


def test_no_context_round_029():
    # Arrange
    dummy = DummySelf()
    web_context = ""  # empty
    mcp_context = []
    sub_query = "none"

    # Act
    result = ResearchConductor._combine_mcp_and_web_context(dummy, mcp_context, web_context, sub_query)

    # Assert empty string returned when no parts
    assert result == ""

    # Warning should have been emitted
    expected_warn = f"No context to combine for sub-query: {sub_query}"
    assert dummy.logger.warn_msgs and dummy.logger.warn_msgs[-1] == expected_warn
