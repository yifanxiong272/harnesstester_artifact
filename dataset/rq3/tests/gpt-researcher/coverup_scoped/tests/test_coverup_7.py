# file: gpt_researcher/mcp/tool_selector.py:35-127
# asked: {"lines": [35, 47, 48, 50, 51, 53, 56, 57, 58, 59, 60, 61, 63, 66, 69, 71, 73, 75, 76, 77, 80, 81, 84, 85, 86, 88, 89, 90, 91, 92, 93, 94, 95, 97, 98, 100, 103, 104, 105, 106, 107, 109, 110, 111, 113, 114, 115, 118, 119, 121, 122, 124, 125, 126, 127], "branches": [[47, 48], [47, 50], [50, 51], [50, 53], [57, 58], [57, 66], [75, 76], [75, 80], [90, 91], [90, 97], [103, 104], [103, 113], [109, 103], [109, 110], [113, 114], [113, 118]]}
# gained: {"lines": [35, 47, 50, 51, 53, 56, 57, 58, 59, 60, 61, 63, 66, 69, 71, 73, 75, 76, 77, 80, 81, 84, 85, 86, 88, 89, 90, 91, 92, 93, 94, 95, 100, 103, 104, 105, 106, 107, 109, 110, 111, 113, 114, 115, 118, 119, 121, 122, 124, 125, 126, 127], "branches": [[47, 50], [50, 51], [50, 53], [57, 58], [57, 66], [75, 76], [75, 80], [90, 91], [103, 104], [103, 113], [109, 103], [109, 110], [113, 114], [113, 118]]}

import types
import sys
import pytest
import asyncio
import json

from gpt_researcher.mcp.tool_selector import MCPToolSelector


class SimpleTool:
    def __init__(self, name, description=None):
        self.name = name
        self.description = description


def _install_promptfamily(monkeypatch):
    """
    Ensure that the module gpt_researcher.prompts exists with PromptFamily.generate_mcp_tool_selection_prompt.
    This mirrors the relative import '..prompts' inside the implementation.
    """
    mod_name = "gpt_researcher.prompts"
    mod = types.ModuleType(mod_name)

    class PromptFamily:
        @staticmethod
        def generate_mcp_tool_selection_prompt(query, tools_info, max_tools):
            # Return something trivial; content is not important for the tested logic.
            return f"PROMPT_FOR:{query}:MAX={max_tools}:TOOLS={len(tools_info)}"

    mod.PromptFamily = PromptFamily
    # Insert/replace in sys.modules
    monkeypatch.setitem(sys.modules, mod_name, mod)
    return mod


@pytest.mark.asyncio
async def test_select_relevant_tools_falsy_response_returns_fallback(monkeypatch):
    _install_promptfamily(monkeypatch)

    selector = MCPToolSelector(cfg=None)

    # Prepare a single tool so len(all_tools) < max_tools branch is taken
    tools = [SimpleTool("tool1", "a tool")]

    # Patch the async LLM call to return an empty string (falsy)
    async def fake_call_llm(prompt):
        return ""

    monkeypatch.setattr(selector, "_call_llm_for_tool_selection", fake_call_llm)

    # Patch fallback to a known sentinel list and ensure it's called
    sentinel = ["FALLBACK"]
    monkeypatch.setattr(selector, "_fallback_tool_selection", lambda all_tools, max_tools: sentinel)

    result = await selector.select_relevant_tools("query", tools, max_tools=3)
    assert result is sentinel
    # ensure we didn't mutate the provided tools
    assert tools[0].name == "tool1"


@pytest.mark.asyncio
async def test_select_relevant_tools_extracts_json_and_selects_tool(monkeypatch):
    _install_promptfamily(monkeypatch)

    selector = MCPToolSelector(cfg=None)

    # Tool with None description to exercise "No description available"
    tool = SimpleTool("selected_tool", None)
    tools = [tool]

    # Use pure JSON string so the initial json.loads(response) path is taken
    response_json = {
        "selected_tools": [
            {"index": 0, "name": "selected_tool", "reason": "match", "relevance_score": 0.95}
        ],
        "selection_reasoning": "Because it's relevant"
    }
    response_text = json.dumps(response_json)

    async def fake_call_llm(prompt):
        return response_text

    monkeypatch.setattr(selector, "_call_llm_for_tool_selection", fake_call_llm)

    result = await selector.select_relevant_tools("find tool", tools, max_tools=3)
    # Should return the actual tool object from tools (index 0)
    assert isinstance(result, list)
    assert result == [tool]


@pytest.mark.asyncio
async def test_select_relevant_tools_malformed_extracted_json_returns_fallback(monkeypatch):
    _install_promptfamily(monkeypatch)

    selector = MCPToolSelector(cfg=None)
    tools = [SimpleTool("t1", "d1"), SimpleTool("t2", "d2")]

    # Response contains braces but invalid JSON inside -> extraction will succeed but json.loads will fail
    response_text = "prefix {not: valid, json: } suffix"

    async def fake_call_llm(prompt):
        return response_text

    monkeypatch.setattr(selector, "_call_llm_for_tool_selection", fake_call_llm)

    sentinel = ["fallback_malformed"]
    monkeypatch.setattr(selector, "_fallback_tool_selection", lambda all_tools, max_tools: sentinel)

    result = await selector.select_relevant_tools("q", tools, max_tools=2)
    assert result is sentinel


@pytest.mark.asyncio
async def test_select_relevant_tools_no_selected_tools_returns_fallback(monkeypatch):
    _install_promptfamily(monkeypatch)

    selector = MCPToolSelector(cfg=None)
    tools = [SimpleTool("t1", "d1")]

    # Valid JSON but selected_tools contains indexes out of range so no tools selected
    response_json = {
        "selected_tools": [
            {"index": 99, "name": "unknown", "reason": "nope", "relevance_score": 0}
        ],
        "selection_reasoning": "no valid picks"
    }
    response_text = json.dumps(response_json)

    async def fake_call_llm(prompt):
        return response_text

    monkeypatch.setattr(selector, "_call_llm_for_tool_selection", fake_call_llm)

    sentinel = ["fallback_no_selection"]
    monkeypatch.setattr(selector, "_fallback_tool_selection", lambda all_tools, max_tools: sentinel)

    result = await selector.select_relevant_tools("q", tools, max_tools=1)
    assert result is sentinel


@pytest.mark.asyncio
async def test_select_relevant_tools_call_raises_exception_returns_fallback(monkeypatch):
    _install_promptfamily(monkeypatch)

    selector = MCPToolSelector(cfg=None)
    tools = [SimpleTool("t1", "d1")]

    async def raise_exc(prompt):
        raise RuntimeError("LLM failure")

    monkeypatch.setattr(selector, "_call_llm_for_tool_selection", raise_exc)

    sentinel = ["fallback_on_exception"]
    monkeypatch.setattr(selector, "_fallback_tool_selection", lambda all_tools, max_tools: sentinel)

    result = await selector.select_relevant_tools("q", tools, max_tools=1)
    assert result is sentinel
