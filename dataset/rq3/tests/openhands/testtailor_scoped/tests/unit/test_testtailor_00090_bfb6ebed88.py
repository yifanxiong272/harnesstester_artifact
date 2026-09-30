import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.controller.agent')
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
        """Test that Agent.prompt_manager returns the stored PromptManager instance when initialized."""
        # Minimal concrete Agent implementation that doesn't call the abstract base __init__
        class DummyPromptManager:
            pass

        class ConcreteAgent(Agent):
            def __init__(self):
                # Do not call super().__init__ to avoid needing config/llm_registry;
                # only set attributes necessary for the property under test.
                self._prompt_manager = None

            def step(self, state):
                raise NotImplementedError

        agent = ConcreteAgent()
        pm = DummyPromptManager()
        agent._prompt_manager = pm

        # Accessing the property should return the exact object we set
        self.assertIs(agent.prompt_manager, pm)
