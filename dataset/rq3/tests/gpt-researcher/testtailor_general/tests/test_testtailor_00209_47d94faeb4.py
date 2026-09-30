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
        """When len(all_tools) < max_tools, ensure max_tools is reduced and fallback selection is used."""
        # Minimal tool-like objects
        class Tool:
            def __init__(self, name, description):
                self.name = name
                self.description = description

        # Two tools (less than default max_tools=3) to trigger the branch where max_tools is set to len(all_tools)
        tools = [
            Tool("web_search", "A tool to search the web and retrieve results"),
            Tool("file_reader", "Read files and fetch relevant content")
        ]

        selector = MCPToolSelector(cfg=None)

        # Patch the LLM call to return empty string so fallback selection is used
        async def fake_call(prompt: str) -> str:
            return ""

        selector._call_llm_for_tool_selection = fake_call

        # Run the async selection synchronously
        loop = asyncio.get_event_loop()
        selected = loop.run_until_complete(selector.select_relevant_tools("Find recent papers about X", tools))

        # Expect fallback to select available research-relevant tools (both tools match patterns) and len == len(tools)
        self.assertIsInstance(selected, list)
        self.assertEqual(len(selected), len(tools))
        # Ensure returned objects are the same instances (order preserved by scoring)
        self.assertEqual(selected, tools)
