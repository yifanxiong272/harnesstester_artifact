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
        """Verify that the prompt_manager property returns the underlying _prompt_manager when set."""
        # Create a simple sentinel prompt manager
        class DummyPromptManager:
            pass

        pm = DummyPromptManager()

        # Minimal concrete Agent that does not call the base __init__
        class TestAgent(Agent):
            def __init__(self, prompt_manager):
                # Intentionally avoid calling super().__init__ to keep the test simple
                self._prompt_manager = prompt_manager

            def step(self, state):
                raise NotImplementedError

        agent = TestAgent(pm)

        # Accessing prompt_manager should return the exact object we set (no ValueError)
        self.assertIs(agent.prompt_manager, pm)
