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
        """Verify initialization assigns defaults, reads env var for API key,
        sets output_dir as Path, leaves _client None, and detects imagen models.
        """
        # Preserve any existing env vars to restore later
        old_google = os.environ.get("GOOGLE_API_KEY")
        old_gemini = os.environ.get("GEMINI_API_KEY")
        try:
            # Ensure GEMINI_API_KEY is not interfering
            if "GEMINI_API_KEY" in os.environ:
                del os.environ["GEMINI_API_KEY"]

            # Case 1: No model_name/api_key provided -> use DEFAULT_MODEL and GOOGLE_API_KEY from env
            os.environ["GOOGLE_API_KEY"] = "env-test-key-123"
            provider = ImageGeneratorProvider(model_name=None, api_key=None, output_dir="test_outputs")

            # Defaults and assignments
            self.assertEqual(provider.model_name, provider.DEFAULT_MODEL)
            self.assertEqual(provider.api_key, "env-test-key-123")
            self.assertIsNone(provider._client)
            self.assertFalse(provider._is_imagen)
            # output_dir should be stored as a Path; compare its string form
            self.assertEqual(str(provider.output_dir), "test_outputs")

            # Case 2: Explicit imagen model and explicit api_key param
            provider2 = ImageGeneratorProvider(model_name="imagen-4.0-generate-001", api_key="explicit-key", output_dir="other_outputs")
            self.assertEqual(provider2.model_name, "imagen-4.0-generate-001")
            self.assertEqual(provider2.api_key, "explicit-key")
            self.assertTrue(provider2._is_imagen)
            self.assertIsNone(provider2._client)
            self.assertEqual(str(provider2.output_dir), "other_outputs")

        finally:
            # Restore env vars
            if old_google is None:
                os.environ.pop("GOOGLE_API_KEY", None)
            else:
                os.environ["GOOGLE_API_KEY"] = old_google

            if old_gemini is None:
                os.environ.pop("GEMINI_API_KEY", None)
            else:
                os.environ["GEMINI_API_KEY"] = old_gemini
