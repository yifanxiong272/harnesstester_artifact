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
        """Ensure get_agent_from_config dispatches to RetryAgent.from_config when type == 'retry'."""
        config = type("Cfg", (), {"type": "retry"})()
        with unittest.mock.patch.object(RetryAgent, "from_config") as mock_from_config:
            mock_from_config.return_value = "RETRY_AGENT_INSTANCE"
            result = get_agent_from_config(config)
            mock_from_config.assert_called_once_with(config)
            self.assertEqual(result, "RETRY_AGENT_INSTANCE")
