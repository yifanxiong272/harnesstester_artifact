import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.llm_provider.image.modelslab_image_generator')
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
        """Ensure a warning is logged when no MODELSLAB API key is present."""
        # Ensure os.getenv returns None to simulate missing environment variable.
        with unittest.mock.patch("os.getenv", return_value=None):
            logger_name = ModelsLabImageGeneratorProvider.__module__
            with self.assertLogs(logger_name, level="WARNING") as cm:
                provider = ModelsLabImageGeneratorProvider(api_key=None)

        # Provider should have no API key configured.
        self.assertFalse(provider.api_key)

        # The expected warning message should have been logged.
        expected = (
            "No ModelsLab API key found. Set MODELSLAB_API_KEY "
            "environment variable to enable image generation."
        )
        self.assertTrue(
            any(expected in message for message in cm.output),
            f"Expected warning not found in logs: {cm.output}"
        )
