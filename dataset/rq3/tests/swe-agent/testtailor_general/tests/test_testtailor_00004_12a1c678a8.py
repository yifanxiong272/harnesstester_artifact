import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.agents')
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
        """Ensure get_agent_from_config returns a RetryAgent when config.type == 'retry'."""
        class DummyRetryConfig:
            type = "retry"
            def model_copy(self, deep: bool = False):
                # Return self to satisfy RetryAgent.__init__ which calls config.model_copy(deep=True)
                return self

        cfg = DummyRetryConfig()
        agent = get_agent_from_config(cfg)
        self.assertIsInstance(agent, RetryAgent)
