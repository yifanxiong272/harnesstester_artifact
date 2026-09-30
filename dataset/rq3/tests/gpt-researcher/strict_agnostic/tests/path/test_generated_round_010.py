import sys
import types
import json
import asyncio
import pytest

from gpt_researcher.mcp.tool_selector import MCPToolSelector

# Minimal tool-like object used for tests
class DummyTool:
    def __init__(self, name, description=None):
        self.name = name
        self.description = description


def _install_fake_prompts_module():
    """Install a fake gpt_researcher.mcp.prompts module with PromptFamily.generate_mcp_tool_selection_prompt
    to avoid importing real code or external resources. Deterministic and self-contained.
    """
    mod_name = "gpt_researcher.mcp.prompts"
    fake_mod = types.ModuleType(mod_name)

    class PromptFamily:
        @staticmethod
        def generate_mcp_tool_selection_prompt(query, tools_info, max_tools):
            # Deterministic prompt representation
            return f"PROMPT: {query} | max:{max_tools} | tools:{len(tools_info)}"

    fake_mod.PromptFamily = PromptFamily
    sys.modules[mod_name] = fake_mod
    return fake_mod


@pytest.mark.asyncio
async def test_empty_all_tools_round_010():
    """When no tools available, function should return empty list immediately (lines 47-48)."""
    _install_fake_prompts_module()
    selector = MCPToolSelector(cfg=None, researcher=None)
    result = await selector.select_relevant_tools("some query", [], max_tools=3)
    assert result == []


@pytest.mark.asyncio
async def test_llm_empty_response_fallback_with_small_toolset_round_010():
    """If LLM returns empty response, the fallback selection should be used.
    Also exercises branch where len(all_tools) < max_tools (lines 50-51) and empty-response branch (75-77).
    """
    _install_fake_prompts_module()
    selector = MCPToolSelector(cfg=None, researcher=None)

    # Provide two tools but ask for more to trigger len(all_tools) < max_tools
    tools = [DummyTool("t0", "d0"), DummyTool("t1", "d1")]

    # Make _call_llm_for_tool_selection return empty response
    async def fake_call_llm(prompt):
        return ""  # empty response triggers fallback

    selector._call_llm_for_tool_selection = fake_call_llm

    # Replace fallback with deterministic sentinel
    sentinel = ["fallback-sentinel"]
    selector._fallback_tool_selection = lambda all_tools, max_tools: sentinel

    result = await selector.select_relevant_tools("q", tools, max_tools=5)
    assert result is sentinel


@pytest.mark.asyncio
async def test_llm_malformed_json_with_embedded_json_round_010():
    """When LLM responds with surrounding text and an embedded JSON object, the regex-extraction path
    should find and parse the JSON and return the selected tool (lines 86-93).
    """
    _install_fake_prompts_module()
    selector = MCPToolSelector(cfg=None, researcher=None)

    tools = [DummyTool("t0", "d0"), DummyTool("t1", "d1")]

    # Response has extra prefix/suffix but contains a JSON object in the middle
    payload = {
        "selected_tools": [
            {"index": 1, "name": "t1", "relevance_score": 0.9, "reason": "match"}
        ],
        "selection_reasoning": "picked best"
    }
    response_text = "LLM says: Hello" + json.dumps(payload) + "--end"

    async def fake_call_llm(prompt):
        return response_text

    selector._call_llm_for_tool_selection = fake_call_llm

    selected = await selector.select_relevant_tools("find tool", tools, max_tools=2)
    # Should return the actual tool object referenced by index 1
    assert isinstance(selected, list)
    assert len(selected) == 1
    assert selected[0] is tools[1]


@pytest.mark.asyncio
async def test_llm_no_json_no_match_fallback_round_010():
    """When LLM response contains no JSON, the code should fall back (lines 96-98).
    """
    _install_fake_prompts_module()
    selector = MCPToolSelector(cfg=None, researcher=None)

    tools = [DummyTool("t0", "d0")]

    async def fake_call_llm(prompt):
        return "this contains no structured data"

    selector._call_llm_for_tool_selection = fake_call_llm
    sentinel = ["fb2"]
    selector._fallback_tool_selection = lambda all_tools, max_tools: sentinel

    result = await selector.select_relevant_tools("q", tools, max_tools=1)
    assert result is sentinel


@pytest.mark.asyncio
async def test_llm_invalid_index_results_in_fallback_round_010():
    """If LLM selects an out-of-range index, no tools are appended and fallback is used (lines 103-115).
    """
    _install_fake_prompts_module()
    selector = MCPToolSelector(cfg=None, researcher=None)

    tools = [DummyTool("only", "d")]

    payload = {"selected_tools": [{"index": 999, "name": "ghost"}]}

    async def fake_call_llm(prompt):
        return json.dumps(payload)

    selector._call_llm_for_tool_selection = fake_call_llm
    sentinel = ["fallback-for-invalid-index"]
    selector._fallback_tool_selection = lambda all_tools, max_tools: sentinel

    result = await selector.select_relevant_tools("q", tools, max_tools=1)
    assert result is sentinel


@pytest.mark.asyncio
async def test_call_llm_raises_exception_triggers_fallback_round_010():
    """If an exception occurs during LLM call, the outer except should trigger and fallback used (lines 124-127).
    """
    _install_fake_prompts_module()
    selector = MCPToolSelector(cfg=None, researcher=None)

    tools = [DummyTool("t0", "d0")]

    async def fake_call_llm(prompt):
        raise RuntimeError("simulated LLM failure")

    selector._call_llm_for_tool_selection = fake_call_llm
    sentinel = ["fallback-on-exception"]
    selector._fallback_tool_selection = lambda all_tools, max_tools: sentinel

    result = await selector.select_relevant_tools("q", tools, max_tools=3)
    assert result is sentinel
