import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.llm_provider.image.image_generator')
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
        """Warns when no API key is provided and no env var is set."""
        with patch.object(os, "getenv", return_value=None):
            with patch.object(logging.Logger, "warning") as mock_warn:
                provider = ImageGeneratorProvider(model_name=None, api_key=None, output_dir="outputs_test")
                # API key should be None when not provided and not in env
                self.assertIsNone(provider.api_key)
                mock_warn.assert_called_once_with(
                    "No Google API key found. Set GOOGLE_API_KEY or GEMINI_API_KEY "
                    "environment variable to enable image generation."
                )
