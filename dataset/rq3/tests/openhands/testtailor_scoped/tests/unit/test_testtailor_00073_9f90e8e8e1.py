import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.agenthub.codeact_agent.codeact_agent')
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
        """When enable_condensation_request is True, the agent's tools should include CondensationRequestTool."""
        # Create a minimal config object with the attributes referenced by _get_tools
        class Cfg:
            pass

        cfg = Cfg()
        cfg.enable_cmd = False
        cfg.enable_think = False
        cfg.enable_finish = False
        cfg.enable_condensation_request = True
        cfg.enable_browsing = False
        cfg.enable_jupyter = False
        cfg.enable_plan_mode = False
        cfg.enable_llm_editor = False
        cfg.enable_editor = False
        cfg.runtime = None

        # Create an incomplete CodeActAgent instance without running __init__
        agent = CodeActAgent.__new__(CodeActAgent)
        # Provide just the attributes needed by _get_tools
        agent.config = cfg
        agent.llm = None  # ensures use_short_tool_desc is False

        tools = agent._get_tools()
        # The CondensationRequestTool constant should be present in the returned tools list
        self.assertIn(CondensationRequestTool, tools)
