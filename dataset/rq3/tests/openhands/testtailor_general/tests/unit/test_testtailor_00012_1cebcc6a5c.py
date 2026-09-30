import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.controller.agent_controller')
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
        """Verify that when a security analyzer is configured and the action already has a non-None
        security_risk, the controller calls the analyzer and overrides the action.security_risk."""
        # Create a dummy action with an existing non-None security_risk
        class DummyAction:
            def __init__(self):
                # Use UNKNOWN so it's clearly set (and not None)
                self.security_risk = ActionSecurityRisk.UNKNOWN

            def __repr__(self):
                return "<DummyAction>"

        action = DummyAction()

        # Create a dummy security analyzer with an async security_risk method
        class DummySecurityAnalyzer:
            async def security_risk(self, action_received):
                # Return a distinct value to confirm override
                return ActionSecurityRisk.HIGH

        analyzer = DummySecurityAnalyzer()

        # Create an AgentController instance without running __init__
        controller = object.__new__(AgentController)
        # Attach the analyzer
        controller.security_analyzer = analyzer

        # Call the async method
        asyncio.get_event_loop().run_until_complete(
            controller._handle_security_analyzer(action)
        )

        # Verify the action.security_risk was overridden by the analyzer's result
        self.assertEqual(action.security_risk, ActionSecurityRisk.HIGH)
