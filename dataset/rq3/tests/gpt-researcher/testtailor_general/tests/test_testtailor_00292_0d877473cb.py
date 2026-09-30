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
        """Test that conduct_research_with_tools uses GenericLLMProvider, binds tools,
        generates prompt via PromptFamily, invokes the LLM, and returns LLM analysis result.
        """
        # Arrange
        query = "test query"
        # Ensure selected_tools is non-empty so the code proceeds past the early return
        class DummyTool:
            def __init__(self, name):
                self.name = name
        selected_tools = [DummyTool("dummy_tool")]

        # Minimal cfg object expected by MCPResearchSkill
        class Cfg:
            strategic_llm_model = "test-model"
            llm_kwargs = {"foo": "bar"}
            strategic_llm_provider = "test-provider"

        cfg = Cfg()

        # Determine module/package context for relative imports used in the method under test
        module_name = MCPResearchSkill.__module__
        package = module_name.rpartition('.')[0]
        parent = package.rpartition('.')[0]

        if parent:
            generic_mod_name = f"{parent}.llm_provider.generic.base"
            prompts_mod_name = f"{parent}.prompts"
        else:
            generic_mod_name = "llm_provider.generic.base"
            prompts_mod_name = "prompts"

        # Use __import__ to obtain sys and types without top-level imports
        sys = __import__('sys')
        types = __import__('types')

        # Create fake modules
        generic_mod = types.ModuleType(generic_mod_name)
        prompts_mod = types.ModuleType(prompts_mod_name)

        # Stubs to capture calls
        class ResponseStub:
            def __init__(self, content, tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls or []

        class LLMStub:
            def __init__(self):
                self.bound_tools = None
                self.last_messages = None

            def bind_tools(self, tools):
                self.bound_tools = tools
                return self

            async def ainvoke(self, messages):
                # capture messages and return a response with content only
                self.last_messages = messages
                return ResponseStub(content="analysis-text", tool_calls=[])

        # GenericLLMProvider stub that records invocation
        class GenericLLMProvider:
            last_from_provider_args = None

            def __init__(self, provider_name, **kwargs):
                self.provider_name = provider_name
                self.kwargs = kwargs
                self.llm = LLMStub()

            @classmethod
            def from_provider(cls, provider_name, **kwargs):
                cls.last_from_provider_args = {"provider": provider_name, **kwargs}
                return cls(provider_name, **kwargs)

        # PromptFamily stub
        class PromptFamily:
            last_generated = None

            @staticmethod
            def generate_mcp_research_prompt(q, tools):
                PromptFamily.last_generated = (q, tools)
                return f"PROMPT:{q}"

        # Attach stubs to the fake modules
        generic_mod.GenericLLMProvider = GenericLLMProvider
        prompts_mod.PromptFamily = PromptFamily

        # Install fake modules into sys.modules so the relative imports inside the method resolve
        inserted = {}
        try:
            for name, mod in ((generic_mod_name, generic_mod), (prompts_mod_name, prompts_mod)):
                if name in sys.modules:
                    inserted[name] = sys.modules[name]
                sys.modules[name] = mod

            # Instantiate the skill and run the coroutine
            skill = MCPResearchSkill(cfg)

            # Run the async method
            loop = asyncio.get_event_loop()
            results = loop.run_until_complete(skill.conduct_research_with_tools(query, selected_tools))

            # Assert: GenericLLMProvider.from_provider was called with the expected provider and kwargs
            expected_kwargs = {"model": cfg.strategic_llm_model, **cfg.llm_kwargs}
            recorded = GenericLLMProvider.last_from_provider_args
            self.assertIsNotNone(recorded, "GenericLLMProvider.from_provider was not called")
            self.assertEqual(recorded.get("provider"), cfg.strategic_llm_provider)
            # Check model and one llm_kwargs key
            self.assertEqual(recorded.get("model"), expected_kwargs["model"])
            self.assertEqual(recorded.get("foo"), expected_kwargs["foo"])

            # Assert: PromptFamily was used to generate the prompt
            self.assertEqual(PromptFamily.last_generated, (query, selected_tools))

            # Assert: LLM was invoked and results contain LLM analysis
            self.assertIsInstance(results, list)
            # Should include LLM analysis as one result (no tool_calls => only analysis)
            self.assertEqual(len(results), 1)
            result = results[0]
            self.assertIn("LLM Analysis", result.get("title", ""))
            self.assertEqual(result.get("body"), "analysis-text")
            self.assertEqual(result.get("href"), "mcp://llm_analysis")

        finally:
            # Restore any previously loaded modules
            for name in (generic_mod_name, prompts_mod_name):
                if name in inserted:
                    sys.modules[name] = inserted[name]
                else:
                    sys.modules.pop(name, None)
