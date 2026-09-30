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
        """When api_key starts with '$' but the referenced environment variable is not set,
        get_api_keys should log a warning and return an empty list.
        """
        env_name = "SWEA_MISSING_API"
        # Ensure the environment variable is not set
        os.environ.pop(env_name, None)

        cfg = GenericAPIModelConfig(name="gpt-test", api_key=SecretStr(f"${env_name}"))
        result = cfg.get_api_keys()
        self.assertEqual(result, [])
