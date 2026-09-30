import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.action_sampler')
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
        """Ensure AskColleaguesConfig.get returns an AskColleagues instance with the same config."""
        cfg = AskColleaguesConfig()

        class DummyModel(AbstractModel):
            # Intentionally avoid calling super().__init__ to keep this lightweight for the test.
            def __init__(self):
                pass

            def query(self, history, action_prompt: str = "> ", n: int | None = None) -> dict:
                return {}

        model = DummyModel()
        tools = object()  # minimal stand-in for ToolHandler

        result = cfg.get(model, tools)

        self.assertIsInstance(result, AskColleagues)
        # AskColleagues.__init__ stores the provided config on .config
        self.assertIs(result.config, cfg)
