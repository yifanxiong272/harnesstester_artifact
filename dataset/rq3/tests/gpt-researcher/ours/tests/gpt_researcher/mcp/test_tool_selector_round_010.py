import asyncio
import sys
import types
import json
import pytest

from gpt_researcher.mcp import tool_selector

# Minimal tool-like object used by the selector
class SimpleTool:
    def __init__(self, name, description=None):
        self.name = name
        self.description = description


def _ensure_prompt_module():
    """Ensure a dummy gpt_researcher.prompts module exists with PromptFamily
    that exposes generate_mcp_tool_selection_prompt. The real import in the
    source is done inside the function under test, so providing this module
    in sys.modules is enough for deterministic behavior.
    """
    mod_name = "gpt_researcher.prompts"
    if mod_name in sys.modules:
        return
    mod = types.ModuleType(mod_name)

    class PromptFamily:
        @staticmethod
        def generate_mcp_tool_selection_prompt(query, tools_info, max_tools):
            # Deterministic prompt content used by tests; content itself is not
            # interpreted by our patched LLM call.
            return f"PROMPT(query={query},tools={len(tools_info)},max={max_tools})"

    mod.PromptFamily = PromptFamily
    sys.modules[mod_name] = mod


async def _async_return(value):
    return value


async def _async_raise(exc):
    raise exc


def _make_selector():
    # Construct an instance without calling __init__ to avoid any unknown
    # constructor side effects. Tests only require the methods used in
    # select_relevant_tools, which we will patch directly on the instance.
    cls = tool_selector.MCPToolSelector
    inst = cls.__new__(cls)
    return inst


def test_empty_all_tools_round_010():
    """When all_tools is empty the method should immediately return an empty list."""
    selector = _make_selector()

    result = asyncio.run(selector.select_relevant_tools("query", [], max_tools=3))

    assert result == [], "Expected empty list when no tools are provided"


def test_select_single_tool_with_index_adjustment_round_010():
    """If len(all_tools) < max_tools, max_tools should be adjusted and a valid
    JSON LLM response should yield the corresponding tool(s).
    """
    _ensure_prompt_module()
    selector = _make_selector()

    tools = [SimpleTool("T1", "d1")]

    # Patch the LLM call to return valid JSON selecting index 0
    async def mocked_call(prompt):
        return json.dumps({
            "selected_tools": [{"index": 0, "name": "T1", "reason": "good", "relevance_score": 0.9}],
            "selection_reasoning": "because"
        })

    selector._call_llm_for_tool_selection = mocked_call

    # Fallback should not be invoked in this case; make it raise if called
    def fallback(all_tools, max_tools):
        raise AssertionError("Fallback should not be called for valid selection")

    selector._fallback_tool_selection = fallback

    # max_tools deliberately larger than available tools to trigger adjustment
    selected = asyncio.run(selector.select_relevant_tools("q", tools, max_tools=5))

    assert len(selected) == 1
    assert selected[0] is tools[0]
    assert selected[0].name == "T1"


def test_embedded_json_response_round_010():
    """If the LLM response is not pure JSON but contains an embedded JSON object,
    the implementation should extract and parse that JSON.
    """
    _ensure_prompt_module()
    selector = _make_selector()

    tools = [SimpleTool("A", "desc")]

    embedded = "Some commentary... {\"selected_tools\": [{\"index\": 0, \"name\": \"A\", \"reason\": \"ok\"}], \"selection_reasoning\": \"r\"} END"

    async def mocked_call(prompt):
        return embedded

    selector._call_llm_for_tool_selection = mocked_call
    selector._fallback_tool_selection = lambda at, mt: ["FALLBACK"]

    selected = asyncio.run(selector.select_relevant_tools("q2", tools, max_tools=3))

    assert isinstance(selected, list)
    assert selected and selected[0] is tools[0]


def test_no_json_in_response_uses_fallback_round_010():
    """When the LLM response contains no JSON at all, the method should call
    the fallback selection and return its result.
    """
    _ensure_prompt_module()
    selector = _make_selector()

    tools = [SimpleTool("X", None), SimpleTool("Y", "d")]

    async def mocked_call(prompt):
        return "plain text without json"

    selector._call_llm_for_tool_selection = mocked_call

    # deterministic fallback value
    fallback_value = [tools[1]]

    selector._fallback_tool_selection = lambda all_tools, max_tools: fallback_value

    result = asyncio.run(selector.select_relevant_tools("query", tools, max_tools=2))

    assert result is fallback_value


def test_empty_selected_tools_and_out_of_range_index_round_010():
    """If selected_tools is present but empty, or contains only out-of-range
    indices, the code should fall back.
    """
    _ensure_prompt_module()
    selector = _make_selector()

    tools = [SimpleTool("one"), SimpleTool("two")]

    # Case A: selected_tools is empty
    async def call_empty(prompt):
        return json.dumps({"selected_tools": [], "selection_reasoning": "none"})

    selector._call_llm_for_tool_selection = call_empty
    selector._fallback_tool_selection = lambda all_tools, max_tools: ["FB_EMPTY"]

    res_a = asyncio.run(selector.select_relevant_tools("qq", tools, max_tools=2))
    assert res_a == ["FB_EMPTY"]

    # Case B: selected_tools has out-of-range index -> ignored -> fallback
    async def call_oob(prompt):
        return json.dumps({"selected_tools": [{"index": 999, "name": "n/a"}]})

    selector._call_llm_for_tool_selection = call_oob
    selector._fallback_tool_selection = lambda all_tools, max_tools: ["FB_OOB"]

    res_b = asyncio.run(selector.select_relevant_tools("qq2", tools, max_tools=2))
    assert res_b == ["FB_OOB"]


def test_llm_call_raises_exception_uses_fallback_round_010():
    """If the internal LLM call raises an exception, the method should catch it
    and return the fallback selection.
    """
    _ensure_prompt_module()
    selector = _make_selector()

    tools = [SimpleTool("t1")]

    async def call_raises(prompt):
        raise RuntimeError("boom")

    selector._call_llm_for_tool_selection = call_raises
    selector._fallback_tool_selection = lambda all_tools, max_tools: ["FB_ERR"]

    res = asyncio.run(selector.select_relevant_tools("qerr", tools, max_tools=3))
    assert res == ["FB_ERR"]
