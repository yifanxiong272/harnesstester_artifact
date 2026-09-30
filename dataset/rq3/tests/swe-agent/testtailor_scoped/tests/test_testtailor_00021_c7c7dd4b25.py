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
        """Requesting an agent with an unknown type should raise a ValueError with the expected message."""
        class DummyConfig:
            def __init__(self, t: str):
                self.type = t

        cfg = DummyConfig("mystery")
        with self.assertRaisesRegex(ValueError, r"Unknown agent type: mystery"):
            get_agent_from_config(cfg)
