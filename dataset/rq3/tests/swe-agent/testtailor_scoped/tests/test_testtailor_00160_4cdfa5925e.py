import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.models')
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
        """When choose_api_key_by_thread is False, choose_api_key should return one of the explicitly set keys."""
        cfg = GenericAPIModelConfig(
            name="test-model",
            api_key=SecretStr("key-A:::key-B:::key-C"),
            choose_api_key_by_thread=False,
        )
        chosen = cfg.choose_api_key()
        self.assertIn(chosen, ["key-A", "key-B", "key-C"])
