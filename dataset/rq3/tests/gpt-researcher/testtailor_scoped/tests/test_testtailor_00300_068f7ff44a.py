import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.mcp.research')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """Test that conduct_research_with_tools processes LLM tool_calls and executes matching tools."""
        # Prepare a fake cfg object without using types.SimpleNamespace
        cfg = type("Cfg", (object,), {})()
        cfg.strategic_llm_model = "fake-model"
        cfg.llm_kwargs = {}
        cfg.strategic_llm_provider = "fake-provider"

        # Build fake provider/llm and PromptFamily, and intercept imports by monkeypatching __import__
        # Save original __import__
        if hasattr(__builtins__, "__import__"):
            original_import = __builtins__.__import__
            builtins_is_module = True
        else:
            original_import = __builtins__['__import__']
            builtins_is_module = False

        # Define fake provider/LLM
        class FakeLLM:
            def __init__(self):
                self._bound_tools = None

            def bind_tools(self, tools):
                self._bound_tools = tools

                class Bound:
                    async def ainvoke(self_inner, messages):
                        # Return a response object that contains a tool_calls list and content
                        resp = type("Resp", (), {})()
                        resp.tool_calls = [{"name": "tool-a", "args": {"q": "hello"}}]
                        resp.content = "LLM final analysis"
                        return resp

                return Bound()

        class FakeProvider:
            def __init__(self):
                self.llm = FakeLLM()

            @classmethod
            def from_provider(cls, provider_name, **kwargs):
                return FakeProvider()

        # Define PromptFamily replacement
        class FakePromptFamily:
            @staticmethod
            def generate_mcp_research_prompt(query, selected_tools):
                return f"RESEARCH PROMPT: {query}"

        # Create fake module-like objects to return from our fake import
        class FakeModuleA:
            GenericLLMProvider = FakeProvider

        class FakeModuleB:
            PromptFamily = FakePromptFamily

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            # Intercept the provider import path and the prompts import
            if "llm_provider.generic.base" in name:
                return FakeModuleA
            if name.endswith("prompts") or name.endswith(".prompts") or ".prompts" in name:
                return FakeModuleB
            # Fallback to original import for everything else
            return original_import(name, globals, locals, fromlist, level)

        # Patch __import__
        try:
            if builtins_is_module:
                __builtins__.__import__ = fake_import
            else:
                __builtins__['__import__'] = fake_import

            # Create a tool that matches the name 'tool-a' and has an async ainvoke method
            class FakeTool:
                def __init__(self):
                    self.name = "tool-a"

                async def ainvoke(self, args):
                    # Return a simple MCP-like dict with content as string
                    return {"content": "tool output"}

            selected_tools = [FakeTool()]

            skill = MCPResearchSkill(cfg)

            # Execute the async method
            results = asyncio.get_event_loop().run_until_complete(
                skill.conduct_research_with_tools("search query", selected_tools)
            )

            # Expect two results: one from the tool and one LLM analysis
            self.assertIsInstance(results, list)
            self.assertGreaterEqual(len(results), 2)

            tool_result = results[0]
            llm_result = results[-1]

            # Validate the tool result was processed and contains our tool output
            self.assertIn("body", tool_result)
            self.assertIn("tool output", tool_result["body"])
            self.assertIn("title", tool_result)
            self.assertTrue(tool_result["title"].startswith("Result from") or "Result" in tool_result["title"])

            # Validate the LLM analysis was appended
            self.assertEqual(llm_result.get("href"), "mcp://llm_analysis")
            self.assertIn("LLM final analysis", llm_result.get("body", ""))

        finally:
            # Restore original __import__
            if builtins_is_module:
                __builtins__.__import__ = original_import
            else:
                __builtins__['__import__'] = original_import
