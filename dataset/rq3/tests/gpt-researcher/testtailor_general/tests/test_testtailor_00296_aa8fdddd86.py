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
        """Ensure deprecated EMBEDDING_PROVIDER env var triggers warning and sets provider/model."""
        # Preserve existing environment
        prev_val = os.environ.get("EMBEDDING_PROVIDER")
        os.environ["EMBEDDING_PROVIDER"] = "openai"

        try:
            from unittest.mock import patch
            from gpt_researcher.config import Config

            with patch("warnings.warn") as mock_warn:
                cfg = Config(config_path=None)

                # warnings.warn should have been called for the deprecated env var
                self.assertTrue(mock_warn.called, "Expected a deprecation warning to be emitted.")

                # Verify the deprecation message contains the expected text
                called_args, called_kwargs = mock_warn.call_args
                self.assertIn("EMBEDDING_PROVIDER is deprecated", called_args[0])

                # Verify that the embedding provider/model were set according to the deprecated var
                self.assertEqual(cfg.embedding_provider, "openai")
                self.assertEqual(cfg.embedding_model, "text-embedding-3-large")
        finally:
            # Restore environment
            if prev_val is None:
                del os.environ["EMBEDDING_PROVIDER"]
            else:
                os.environ["EMBEDDING_PROVIDER"] = prev_val
