import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.mcp.tool_selector')
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
        """When max_tools is larger than available tools, it should be reduced to len(all_tools)."""
        # Create minimal tool objects
        class DummyTool:
            def __init__(self, name, description=""):
                self.name = name
                self.description = description

        tools = [DummyTool("search_tool", "search data"), DummyTool("read_tool", "read docs")]

        # Spy selector to capture the max_tools passed into fallback
        class SpySelector(MCPToolSelector):
            def __init__(self, cfg=None, researcher=None):
                super().__init__(cfg=cfg, researcher=researcher)
                self.captured_max_tools = None

            # Force LLM call to return empty so fallback is used
            async def _call_llm_for_tool_selection(self, prompt: str) -> str:
                return ""

            def _fallback_tool_selection(self, all_tools, max_tools: int):
                # Capture the value of max_tools received by fallback
                self.captured_max_tools = max_tools
                # Return an empty list for simplicity
                return []

        selector = SpySelector(cfg=None)

        # Call the async select_relevant_tools
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(selector.select_relevant_tools("find information", tools, max_tools=5))

        # The fallback should have been invoked and captured_max_tools should be reduced to len(tools)
        self.assertEqual(selector.captured_max_tools, len(tools))
        # And the returned result should be whatever our fallback returned (empty list)
        self.assertEqual(result, [])
