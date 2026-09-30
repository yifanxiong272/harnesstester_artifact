import sys
import types
import asyncio
from types import SimpleNamespace
import pytest

from gpt_researcher.mcp.research import MCPResearchSkill


class DummyResponse:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


def _inject_fake_modules(response):
    """Inject fake GenericLLMProvider and PromptFamily into sys.modules.
    The GenericLLMProvider.from_provider will return an object with an llm
    that has bind_tools(selected_tools) -> object with async def ainvoke(messages)
    which returns the provided response.
    """
    # Create fake prompts module
    prompts_mod = types.ModuleType("gpt_researcher.prompts")

    class PromptFamily:
        @staticmethod
        def generate_mcp_research_prompt(query, tools):
            # deterministic prompt content based on inputs
            return f"PROMPT:{query}:{len(tools)}"

    prompts_mod.PromptFamily = PromptFamily

    # Create fake llm provider module path
    base_mod = types.ModuleType("gpt_researcher.llm_provider.generic.base")

    class _LLMWithTools:
        def __init__(self, response):
            self._response = response

        async def ainvoke(self, messages):
            # Return the provided response object deterministically
            return self._response

        def bind_tools(self, tools):
            # binding returns self - caller expects object with ainvoke
            return self

    class GenericLLMProvider:
        def __init__(self, response):
            self.llm = _LLMWithTools(response)

        @staticmethod
        def from_provider(provider_name, **kwargs):
            # ignore inputs, return a provider whose .llm.bind_tools returns object
            return GenericLLMProvider(response)

    base_mod.GenericLLMProvider = GenericLLMProvider

    # Insert into sys.modules so the in-function imports resolve
    sys.modules["gpt_researcher.prompts"] = prompts_mod
    sys.modules["gpt_researcher.llm_provider.generic.base"] = base_mod


def test_no_tools_round_008():
    """When selected_tools is empty, function should early-return an empty list."""
    cfg = SimpleNamespace(strategic_llm_model="m", llm_kwargs={}, strategic_llm_provider="p")
    skill = MCPResearchSkill(cfg)

    results = asyncio.run(skill.conduct_research_with_tools("query", []))

    assert results == []


def test_llm_only_content_round_008(monkeypatch):
    """If LLM returns no tool_calls but has content, that content is returned as LLM Analysis."""
    # Response with no tool_calls but with content
    response = DummyResponse(content="This is LLM analysis", tool_calls=None)

    # Inject the fake provider and prompts that will return our response
    _inject_fake_modules(response)

    cfg = SimpleNamespace(strategic_llm_model="m", llm_kwargs={}, strategic_llm_provider="p")
    skill = MCPResearchSkill(cfg)

    # Run the async function deterministically
    results = asyncio.run(skill.conduct_research_with_tools("my query", [SimpleNamespace(name="unused")]))

    # Expect a single LLM analysis entry constructed from response.content
    assert any(r.get("title", "").startswith("LLM Analysis: my query") for r in results)
    assert any(r.get("body", "") == "This is LLM analysis" for r in results)


def test_tool_calls_multiple_branches_round_008(monkeypatch):
    """Exercise branches for tool_calls handling: sync invoke, async ainvoke and callable tool.
    Also exercise the tool_args truthy branch where args are converted into a string.
    """
    # Build tool_calls with args to trigger args_str branch
    tool_calls = [
        {"name": "sync_tool", "args": {"q": "1"}},
        {"name": "async_tool", "args": {"a": 2}},
        {"name": "callable_tool", "args": {"x": "y"}},
        {"name": "missing_tool", "args": {"z": 3}},
    ]

    response = DummyResponse(content="LLM final content", tool_calls=tool_calls)

    # Prepare fake modules that will return this response
    _inject_fake_modules(response)

    cfg = SimpleNamespace(strategic_llm_model="m", llm_kwargs={}, strategic_llm_provider="p")
    skill = MCPResearchSkill(cfg)

    # Prepare selected tools:
    class SyncTool:
        def __init__(self, name):
            self.name = name

        def invoke(self, args):
            return {"sync": True, "args": args}

    class AsyncTool:
        def __init__(self, name):
            self.name = name

        async def ainvoke(self, args):
            return {"async": True, "args": args}

    class CallableTool:
        def __init__(self, name):
            self.name = name

        def __call__(self, args):
            return {"callable": True, "args": args}

    selected_tools = [SyncTool("sync_tool"), AsyncTool("async_tool"), CallableTool("callable_tool")]

    # Capture calls to _process_tool_result and return predictable formatted results
    processed = []

    def fake_process(tool_name, result):
        processed.append((tool_name, result))
        # Return a formatted result list for that tool
        return [{"title": f"{tool_name}-title", "body": str(result)}]

    monkeypatch.setattr(skill, "_process_tool_result", fake_process)

    results = asyncio.run(skill.conduct_research_with_tools("important query", selected_tools))

    # Verify that _process_tool_result was called for the three found tools (missing_tool not in selected_tools)
    called_tool_names = [c[0] for c in processed]
    assert "sync_tool" in called_tool_names
    assert "async_tool" in called_tool_names
    assert "callable_tool" in called_tool_names
    assert "missing_tool" not in called_tool_names

    # Verify that returned results include formatted entries and include LLM analysis
    titles = [r.get("title") for r in results]
    # formatted results should appear
    assert any(t and t.endswith("-title") for t in titles)
    # LLM analysis entry should be present
    assert any(r.get("href") == "mcp://llm_analysis" and "LLM Analysis" in r.get("title", "") for r in results)
