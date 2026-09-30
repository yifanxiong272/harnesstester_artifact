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
        """When EMBEDDING_PROVIDER is set to 'ollama', ensure OLLAMA_EMBEDDING_MODEL is used."""
        # Ensure the environment variables for the deprecated embedding provider are present
        with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "ollama", "OLLAMA_EMBEDDING_MODEL": "ollama-embedding-v1"}):
            # Instantiate the Config which will run _handle_deprecated_attributes in __init__
            cfg = Config(config_path=None)

            # The deprecated EMBEDDING_PROVIDER should override the parsed embedding provider
            self.assertEqual(cfg.embedding_provider, "ollama")
            # The OLLAMA_EMBEDDING_MODEL env var should be assigned to embedding_model
            self.assertEqual(cfg.embedding_model, "ollama-embedding-v1")
