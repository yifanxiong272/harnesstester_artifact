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
        """Ensure API keys specified as an env var (starts with $) are resolved and split by :::"""
        os.environ["SWEA_TEST_KEY"] = "envkey1:::envkey2"
        try:
            cfg = GenericAPIModelConfig(
                name="gpt-4o",
                completion_kwargs={"mock_response": "Env Hello"},
                api_key=SecretStr("$SWEA_TEST_KEY"),
                top_p=None,
            )
            # get_api_keys should resolve the env var and split into two keys
            self.assertEqual(cfg.get_api_keys(), ["envkey1", "envkey2"])
        finally:
            del os.environ["SWEA_TEST_KEY"]
