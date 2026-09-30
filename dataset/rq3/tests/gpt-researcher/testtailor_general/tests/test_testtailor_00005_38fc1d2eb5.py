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
        """Test initialization sets defaults, reads env API key, and detects 'imagen' models."""
        # Preserve environment
        original_google_key = os.environ.get("GOOGLE_API_KEY")
        original_gemini_key = os.environ.get("GEMINI_API_KEY")

        try:
            # Ensure env has a key for the first part of the test
            os.environ.pop("GEMINI_API_KEY", None)
            os.environ["GOOGLE_API_KEY"] = "env_key_123"

            # 1) No model_name and no api_key param -> use DEFAULT_MODEL and env key
            provider = ImageGeneratorProvider()
            self.assertEqual(provider.model_name, provider.DEFAULT_MODEL)
            self.assertEqual(provider.api_key, "env_key_123")
            self.assertIsNone(provider._client)
            # DEFAULT_MODEL is a Gemini model, should NOT be detected as Imagen
            self.assertFalse(provider._is_imagen)
            # output_dir should be the default string "outputs" when stringified
            self.assertEqual(str(provider.output_dir), "outputs")

            # 2) Provide explicit api_key and an Imagen model name -> _is_imagen True
            tmp_dir = f"tmp_imgprov_{os.getpid()}_{os.urandom(4).hex()}"
            os.makedirs(tmp_dir, exist_ok=True)
            try:
                provider2 = ImageGeneratorProvider(
                    model_name="imagen-4.0-generate-001",
                    api_key="param_key_456",
                    output_dir=tmp_dir,
                )
                self.assertEqual(provider2.model_name, "imagen-4.0-generate-001")
                self.assertEqual(provider2.api_key, "param_key_456")
                self.assertIsNone(provider2._client)
                self.assertTrue(provider2._is_imagen)
                self.assertEqual(str(provider2.output_dir), tmp_dir)
            finally:
                # Clean up the created directory (should be empty)
                try:
                    os.rmdir(tmp_dir)
                except Exception:
                    # If removal fails for any reason, ignore to not break test cleanup
                    pass

            # 3) If GEMINI_API_KEY present and GOOGLE_API_KEY missing, it should be picked up
            os.environ.pop("GOOGLE_API_KEY", None)
            os.environ["GEMINI_API_KEY"] = "gemini_env_key"
            provider3 = ImageGeneratorProvider(model_name="models/gemini-2.5-flash-image")
            self.assertEqual(provider3.api_key, "gemini_env_key")
            self.assertFalse(provider3._is_imagen)

        finally:
            # Restore environment
            if original_google_key is None:
                os.environ.pop("GOOGLE_API_KEY", None)
            else:
                os.environ["GOOGLE_API_KEY"] = original_google_key

            if original_gemini_key is None:
                os.environ.pop("GEMINI_API_KEY", None)
            else:
                os.environ["GEMINI_API_KEY"] = original_gemini_key
