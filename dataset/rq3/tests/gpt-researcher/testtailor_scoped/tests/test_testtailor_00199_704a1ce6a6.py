import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.config.config')
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
        """When EMBEDDING_PROVIDER env var is set, Config should warn and set provider/model accordingly."""
        # Ensure EMBEDDING_PROVIDER triggers the deprecation branch and sets expected model for 'openai'
        with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "openai"}, clear=False):
            with patch("warnings.warn") as mock_warn:
                cfg = Config(config_path=None)  # initialize to trigger _handle_deprecated_attributes
                # warnings.warn should have been called for deprecated EMBEDDING_PROVIDER
                mock_warn.assert_called()
                # embedding_provider should be updated from the environment
                self.assertEqual(cfg.embedding_provider, "openai")
                # for 'openai' provider the code sets a specific model
                self.assertEqual(cfg.embedding_model, "text-embedding-3-large")
