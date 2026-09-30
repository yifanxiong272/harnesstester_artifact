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
        """When EMBEDDING_PROVIDER is 'custom', embedding_model should come from OPENAI_EMBEDDING_MODEL or default to 'custom'."""
        # Case 1: OPENAI_EMBEDDING_MODEL is set -> embedding_model should be that value
        with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "custom", "OPENAI_EMBEDDING_MODEL": "my-custom-model"}):
            cfg = Config.__new__(Config)
            # initialize attributes that the handler may reference
            cfg.embedding_provider = None
            cfg.embedding_model = None
            cfg.fast_llm_provider = None
            cfg.smart_llm_provider = None
            cfg.fast_llm_model = None
            cfg.smart_llm_model = None

            cfg._handle_deprecated_attributes()

            self.assertEqual(cfg.embedding_provider, "custom")
            self.assertEqual(cfg.embedding_model, "my-custom-model")

        # Case 2: OPENAI_EMBEDDING_MODEL not set -> embedding_model should default to "custom"
        with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "custom"}):
            # Ensure OPENAI_EMBEDDING_MODEL is not present
            os.environ.pop("OPENAI_EMBEDDING_MODEL", None)

            cfg2 = Config.__new__(Config)
            cfg2.embedding_provider = None
            cfg2.embedding_model = "initial-value"
            cfg2.fast_llm_provider = None
            cfg2.smart_llm_provider = None
            cfg2.fast_llm_model = None
            cfg2.smart_llm_model = None

            cfg2._handle_deprecated_attributes()

            self.assertEqual(cfg2.embedding_provider, "custom")
            self.assertEqual(cfg2.embedding_model, "custom")
