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
        """Ensure a warning is logged when no MODELSLAB_API_KEY is provided."""
        # Ensure environment variable is not set
        os.environ.pop("MODELSLAB_API_KEY", None)

        # Capture warning logs produced during initialization
        with self.assertLogs(level="WARNING") as cm:
            provider = ModelsLabImageGeneratorProvider(model_id=None, api_key=None, output_dir="outputs_test")

        # The provider should have no api_key and should fall back to the default model
        self.assertIsNone(provider.api_key)
        self.assertEqual(provider.model_id, provider.DEFAULT_MODEL)

        # Verify the expected warning message was emitted
        expected_fragment = "No ModelsLab API key found. Set MODELSLAB_API_KEY"
        self.assertTrue(
            any(expected_fragment in message for message in cm.output),
            f"Expected warning not found in logs: {cm.output}"
        )
