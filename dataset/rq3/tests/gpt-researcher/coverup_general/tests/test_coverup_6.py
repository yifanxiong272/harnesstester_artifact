# file: gpt_researcher/mcp/research.py:34-156
# asked: {"lines": [34, 45, 46, 47, 49, 51, 52, 55, 56, 57, 60, 61, 62, 66, 69, 72, 75, 78, 79, 82, 85, 86, 89, 90, 91, 93, 96, 97, 98, 100, 102, 103, 104, 105, 108, 109, 110, 111, 113, 116, 117, 118, 121, 122, 123, 126, 127, 128, 129, 131, 133, 134, 135, 138, 139, 140, 141, 142, 144, 147, 148, 149, 151, 152, 154, 155, 156], "branches": [[45, 46], [45, 49], [85, 86], [85, 138], [89, 90], [89, 138], [96, 97], [96, 100], [103, 104], [103, 108], [108, 109], [108, 110], [110, 111], [110, 113], [116, 117], [116, 131], [126, 89], [126, 127], [138, 139], [138, 151]]}
# gained: {"lines": [34, 45, 46, 47, 49, 51, 52, 55, 56, 57, 60, 61, 62, 66, 69, 72, 75, 78, 79, 82, 85, 86, 89, 90, 91, 93, 96, 97, 98, 100, 102, 103, 104, 105, 108, 109, 110, 111, 113, 116, 117, 118, 121, 122, 123, 126, 127, 128, 129, 131, 133, 134, 135, 138, 139, 140, 141, 142, 144, 147, 148, 149, 151, 152, 154, 155, 156], "branches": [[45, 46], [45, 49], [85, 86], [89, 90], [89, 138], [96, 97], [103, 104], [103, 108], [108, 109], [108, 110], [110, 111], [110, 113], [116, 117], [116, 131], [126, 89], [126, 127], [138, 139]]}

import sys
import types
import asyncio
import pytest

from gpt_researcher.mcp.research import MCPResearchSkill


class DummyCfg:
    def __init__(self):
        self.strategic_llm_model = "dummy-model"
        self.strategic_llm_provider = "dummy-provider"
        self.llm_kwargs = {"temperature": 0.2}


@pytest.mark.asyncio
async def test_no_selected_tools_returns_empty(monkeypatch):
    cfg = DummyCfg()
    skill = MCPResearchSkill(cfg, researcher=None)

    # Call with empty selected tools should immediately return []
    res = await skill.conduct_research_with_tools("query", [])
    assert res == []


@pytest.mark.asyncio
async def test_conduct_research_with_various_tool_types_and_llm_content(monkeypatch):
    # Prepare dummy modules to satisfy internal imports
    # 1) gpt_researcher.llm_provider.generic.base -> GenericLLMProvider
    module_name = "gpt_researcher.llm_provider.generic.base"
    mod = types.ModuleType(module_name)

    class FakeLLM:
        def __init__(self, bound_tools):
            self._bound_tools = bound_tools

        def bind_tools(self, selected_tools):
            # Return an object with ainvoke coroutine
            class BoundLLM:
                def __init__(self, selected_tools):
                    self._selected_tools = selected_tools

                async def ainvoke(self, messages):
                    # Build a response object with tool_calls and content
                    class Response:
                        pass

                    resp = Response()
                    # The tool calls include various tool names (some will not be found)
                    resp.tool_calls = [
                        {"name": "tool_ainvoke", "args": {"q": "1"}},
                        {"name": "tool_invoke", "args": {"x": "2"}},
                        {"name": "tool_func", "args": {"y": "3"}},
                        {"name": "tool_missing", "args": {"z": "4"}},  # not in selected_tools
                        {"name": "tool_empty", "args": {"e": "5"}},
                        {"name": "tool_raises", "args": {"r": "6"}},
                    ]
                    resp.content = "This is the LLM analysis content."
                    return resp

            return BoundLLM(selected_tools)

    class FakeProvider:
        def __init__(self, llm):
            self.llm = llm

        @classmethod
        def from_provider(cls, provider_name, **kwargs):
            # ignore provider_name and kwargs, return a fake provider whose llm returns a BoundLLM when bind_tools called
            return FakeProvider(FakeLLM(bound_tools=None))

    mod.GenericLLMProvider = FakeProvider
    monkeypatch.setitem(sys.modules, module_name, mod)

    # 2) gpt_researcher.prompts -> PromptFamily.generate_mcp_research_prompt
    prompts_mod_name = "gpt_researcher.prompts"
    prompts_mod = types.ModuleType(prompts_mod_name)

    class PromptFamily:
        @staticmethod
        def generate_mcp_research_prompt(query, selected_tools):
            return f"PROMPT for {query}"

    prompts_mod.PromptFamily = PromptFamily
    monkeypatch.setitem(sys.modules, prompts_mod_name, prompts_mod)

    # Prepare cfg and skill
    cfg = DummyCfg()
    skill = MCPResearchSkill(cfg, researcher=None)

    # Monkeypatch the skill's _process_tool_result to a predictable formatter
    processed_calls = []

    def fake_process_tool_result(tool_name, result):
        # Record the call for later assertions and return a predictable formatted result
        processed_calls.append((tool_name, result))
        return [{"title": f"formatted-{tool_name}", "href": f"mcp://{tool_name}", "body": f"body-of-{tool_name}"}]

    monkeypatch.setattr(skill, "_process_tool_result", fake_process_tool_result)

    # Define a number of tools to exercise different branches
    class ToolAInv:
        name = "tool_ainvoke"

        async def ainvoke(self, args):
            return {"data": "A"}

    class ToolInvoke:
        name = "tool_invoke"

        def invoke(self, args):
            return {"data": "B"}

    # async function tool (function objects allow attribute assignment)
    async def tool_func(args):
        return {"data": "C"}

    tool_func.name = "tool_func"

    class ToolEmpty:
        name = "tool_empty"

        def invoke(self, args):
            return ""  # empty result should trigger 'empty result' branch

    class ToolRaises:
        name = "tool_raises"

        def invoke(self, args):
            raise RuntimeError("tool failure")

    selected_tools = [ToolAInv(), ToolInvoke(), tool_func, ToolEmpty(), ToolRaises()]

    # Now call the skill
    results = await skill.conduct_research_with_tools("test query", selected_tools)

    # Assertions:
    # - Processed formatted results should be present for the three successful tools (ainvoke, invoke, func)
    # - The tool_empty should not have produced formatted results (since empty)
    # - The tool_raises should have been caught and skipped
    # - tool_missing was in tool_calls but not in selected_tools, so skipped
    # - LLM analysis should be appended as last result
    # We expect 3 formatted results + 1 LLM analysis = 4
    assert isinstance(results, list)
    assert len(results) == 4

    titles = [r.get("title") for r in results]
    assert "formatted-tool_ainvoke" in titles
    assert "formatted-tool_invoke" in titles
    assert "formatted-tool_func" in titles

    # Check that LLM analysis is present and last
    last = results[-1]
    assert last["title"].startswith("LLM Analysis:")
    assert last["href"] == "mcp://llm_analysis"
    assert last["body"] == "This is the LLM analysis content."

    # Ensure that fake_process_tool_result recorded the expected calls (3 successful)
    processed_names = [name for (name, _) in processed_calls]
    assert set(processed_names) == {"tool_ainvoke", "tool_invoke", "tool_func"}


@pytest.mark.asyncio
async def test_exception_in_llm_provider_returns_empty(monkeypatch):
    # Prepare a module where GenericLLMProvider.from_provider raises
    module_name = "gpt_researcher.llm_provider.generic.base"
    mod = types.ModuleType(module_name)

    class BadProvider:
        @classmethod
        def from_provider(cls, provider_name, **kwargs):
            raise RuntimeError("provider init failed")

    mod.GenericLLMProvider = BadProvider
    monkeypatch.setitem(sys.modules, module_name, mod)

    # prompts module still needed for import inside function
    prompts_mod_name = "gpt_researcher.prompts"
    prompts_mod = types.ModuleType(prompts_mod_name)

    class PromptFamily:
        @staticmethod
        def generate_mcp_research_prompt(query, selected_tools):
            return "irrelevant"

    prompts_mod.PromptFamily = PromptFamily
    monkeypatch.setitem(sys.modules, prompts_mod_name, prompts_mod)

    cfg = DummyCfg()
    skill = MCPResearchSkill(cfg, researcher=None)

    # Provide a non-empty selected_tools to ensure code reaches the try/except
    class DummyTool:
        name = "dummy"

    res = await skill.conduct_research_with_tools("q", [DummyTool()])
    assert res == []
