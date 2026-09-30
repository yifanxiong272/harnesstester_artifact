import pytest

from gpt_researcher.prompts import PromptFamily


class DummyTool:
    def __init__(self, name):
        # ensure name is a string to match branch expectations
        self.name = name


def test_generate_mcp_research_prompt_with_name_attr_round_139():
    """
    Verify that when selected_tools contains objects with a .name attribute,
    the generated prompt includes the tool names as a Python list literal
    in the AVAILABLE TOOLS section and includes the query verbatim.
    """
    query = "What is the impact of AI on healthcare?"
    tools = [DummyTool("ToolA"), DummyTool("ToolB")]

    prompt = PromptFamily.generate_mcp_research_prompt(query, tools)

    # The function inserts the tool_names Python list representation directly.
    assert "RESEARCH QUERY: \"What is the impact of AI on healthcare?\"" in prompt
    # Expect the exact list literal with the names in order
    assert "AVAILABLE TOOLS: ['ToolA', 'ToolB']" in prompt


def test_generate_mcp_research_prompt_with_noname_values_round_139():
    """
    Verify that when selected_tools contains values without a .name attribute
    (e.g., strings, ints, objects without .name), the function falls back to
    str(tool) and includes those stringified values in the AVAILABLE TOOLS list.
    """
    class NoName:
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return f"NoName({self.value})"

    query = "Summarize climate policy developments"
    # mix of a plain string, an int, and an object without .name
    selected = ["plain_string_tool", 42, NoName("X")]

    prompt = PromptFamily.generate_mcp_research_prompt(query, selected)

    assert 'RESEARCH QUERY: "Summarize climate policy developments"' in prompt
    # The list literal should show the stringified representations in order
    # Note: str(42) -> '42', str(NoName("X")) -> 'NoName(X)'
    assert "AVAILABLE TOOLS: ['plain_string_tool', '42', 'NoName(X)']" in prompt
