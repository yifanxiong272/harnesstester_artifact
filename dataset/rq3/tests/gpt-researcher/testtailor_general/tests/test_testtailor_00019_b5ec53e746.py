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
        """Ensure defaults are applied when model_id/api_key are not provided and
        MODELSLAB_API_KEY environment variable is used for the API key.
        """
        # Preserve original environment value
        original_key = os.environ.get("MODELSLAB_API_KEY")
        try:
            # Set environment API key to simulate platform-provided key
            os.environ["MODELSLAB_API_KEY"] = "env-test-key-123"

            provider = ModelsLabImageGeneratorProvider()

            # model_id should default to DEFAULT_MODEL when not provided
            self.assertEqual(provider.model_id, provider.DEFAULT_MODEL)

            # api_key should be taken from the environment variable
            self.assertEqual(provider.api_key, "env-test-key-123")

            # output_dir should be converted to a Path; stringify to avoid extra imports
            self.assertEqual(str(provider.output_dir), "outputs")

            # Provider should report availability since api_key is set
            self.assertTrue(provider.is_available())
        finally:
            # Restore original environment state
            if original_key is None:
                os.environ.pop("MODELSLAB_API_KEY", None)
            else:
                os.environ["MODELSLAB_API_KEY"] = original_key
