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
        """Test that conduct_research_with_tools returns empty list when no tools provided."""
        # Minimal cfg object; not used because method returns early when selected_tools is empty
        cfg = type("Cfg", (), {})()
        skill = MCPResearchSkill(cfg)

        # Call the async method with an empty selected_tools list
        result = asyncio.get_event_loop().run_until_complete(
            skill.conduct_research_with_tools("any query", [])
        )

        # Expect an empty list and no exception
        self.assertEqual(result, [])
