import sys
import types
import asyncio
from types import SimpleNamespace
import pytest

from gpt_researcher.mcp.research import MCPResearchSkill

@pytest.mark.asyncio
async def test_no_tools_round_008():
    """
    When no tools are provided, conduct_research_with_tools should warn and return an empty list.
    Covers branch: if not selected_tools -> return [].
    """
    cfg = SimpleNamespace(strategic_llm_model='any-model', llm_kwargs={}, strategic_llm_provider='any-provider')
    skill = MCPResearchSkill(cfg, None)

    results = await skill.conduct_research_with_tools("some query", [])

    assert results == [], "Expected empty list when no tools are passed"


@pytest.mark.asyncio
async def test_tool_invocations_round_008(monkeypatch):
    """
    Exercises multiple branches:
    - successful async tool invocation via .ainvoke
    - missing tool name in selected_tools (warning + continue)
    - sync .invoke returning falsy (triggers empty-result warning branch)
    - plain callable tool (else branch) executed synchronously
    - inclusion of LLM analysis content as final result
    """
    # 1) Provide a fake GenericLLMProvider via the exact module path used in the function
    base_mod = types.ModuleType("gpt_researcher.llm_provider.generic.base")

    class FakeLLMWithTools:
        def __init__(self, tools):
            self._tools = tools

        async def ainvoke(self, messages):
            # Simulate an LLM response that made multiple tool calls and also has content
            resp = SimpleNamespace()
            resp.tool_calls = [
                {"name": "tool_a", "args": {"x": 1}},
                {"name": "missing_tool", "args": {"y": 2}},
                {"name": "tool_b", "args": {}},
                {"name": "tool_c", "args": None},
            ]
            resp.content = "LLM produced analysis text"
            return resp

    class FakeLLM:
        def bind_tools(self, tools):
            return FakeLLMWithTools(tools)

    class FakeProvider:
        def __init__(self, llm):
            self.llm = llm

        @classmethod
        def from_provider(cls, name, **kwargs):
            # emulate creation using provider name and provider_kwargs
            return cls(FakeLLM())

    base_mod.GenericLLMProvider = FakeProvider
    monkeypatch.setitem(sys.modules, 'gpt_researcher.llm_provider.generic.base', base_mod)

    # 2) Provide a fake PromptFamily used to build the prompt
    prompts_mod = types.ModuleType("gpt_researcher.prompts")

    class PromptFamily:
        @staticmethod
        def generate_mcp_research_prompt(query, tools):
            return f"PROMPT:{query}:{len(tools)}"

    prompts_mod.PromptFamily = PromptFamily
    monkeypatch.setitem(sys.modules, 'gpt_researcher.prompts', prompts_mod)

    # 3) Construct selected tools covering various invocation styles
    calls = []

    class ToolA:
        name = "tool_a"

        async def ainvoke(self, args):
            calls.append(("tool_a", args))
            return {"result": "A"}

    class ToolB:
        name = "tool_b"

        def invoke(self, args):
            calls.append(("tool_b", args))
            # Return falsy value to trigger 'returned empty result' branch
            return None

    def tool_c(args):
        # plain callable (no .ainvoke/.invoke)
        calls.append(("tool_c", args))
        return {"result": "C"}

    # attach name attribute so the selection logic can find it
    tool_c.name = "tool_c"

    selected_tools = [ToolA(), ToolB(), tool_c]

    # 4) Create MCPResearchSkill with a minimal cfg having expected attributes
    cfg = SimpleNamespace(strategic_llm_model='any-model', llm_kwargs={}, strategic_llm_provider='any-provider')
    skill = MCPResearchSkill(cfg, None)

    # Replace the _process_tool_result to record calls and return formatted results
    processed = []

    def fake_process_tool_result(tool_name, result):
        processed.append((tool_name, result))
        # Return a predictable formatted item
        return [{"title": f"{tool_name}-title", "href": f"mcp://{tool_name}", "body": str(result)}]

    monkeypatch.setattr(skill, '_process_tool_result', fake_process_tool_result)

    # 5) Execute
    results = await skill.conduct_research_with_tools("important query", selected_tools)

    # Assertions (observable behavior)
    # - tool_a and tool_c should have been invoked and processed
    assert any(p[0] == 'tool_a' for p in processed), "tool_a should have been processed"
    assert any(p[0] == 'tool_c' for p in processed), "tool_c should have been processed"

    # - tool_b returned falsy, so it should not produce processed entries
    assert not any(p[0] == 'tool_b' for p in processed), "tool_b returned falsy and should not be processed"

    # - the LLM analysis entry (constructed from response.content) should be present
    assert any(r.get('href') == 'mcp://llm_analysis' for r in results), "LLM analysis entry should be present"

    # - results should contain the formatted titles we returned in fake_process_tool_result
    assert any(r.get('title') == 'tool_a-title' for r in results)
    assert any(r.get('title') == 'tool_c-title' for r in results)

    # - ensure the recorded low-level invocations match expectations
    assert ('tool_a', {'x': 1}) in calls
    assert ('tool_b', {}) in calls
    assert ('tool_c', None) in calls
