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
        """Verify __init__ picks defaults, reads MODELSLAB_API_KEY, and converts output_dir to Path-like."""
        # Preserve original environment variable
        original = os.environ.get("MODELSLAB_API_KEY")
        try:
            # Case 1: No api_key passed, environment variable should be used
            os.environ["MODELSLAB_API_KEY"] = "env-key-123"
            # create a unique temporary directory without using tempfile
            tmp_name = f"tmp_modelslab_{os.getpid()}_{id(self)}"
            tmpdir = os.path.join(os.getcwd(), tmp_name)
            os.makedirs(tmpdir, exist_ok=True)
            try:
                provider = ModelsLabImageGeneratorProvider(model_id=None, api_key=None, output_dir=tmpdir)
                # model_id should fall back to DEFAULT_MODEL
                self.assertEqual(provider.model_id, provider.DEFAULT_MODEL)
                # api_key should come from the environment
                self.assertEqual(provider.api_key, "env-key-123")
                # output_dir should reflect the provided directory (Path-like)
                self.assertEqual(str(provider.output_dir), tmpdir)
                self.assertTrue(os.path.isdir(str(provider.output_dir)))
            finally:
                # cleanup created directory
                try:
                    os.rmdir(tmpdir)
                except OSError:
                    # if removal fails, ignore for test cleanup safety
                    pass

            # Case 2: Explicit api_key provided should override environment variable
            os.environ["MODELSLAB_API_KEY"] = "env-key-456"
            tmp_name2 = f"tmp_modelslab2_{os.getpid()}_{id(self)}"
            tmpdir2 = os.path.join(os.getcwd(), tmp_name2)
            os.makedirs(tmpdir2, exist_ok=True)
            try:
                provider2 = ModelsLabImageGeneratorProvider(model_id="custom-model", api_key="explicit-key", output_dir=tmpdir2)
                self.assertEqual(provider2.model_id, "custom-model")
                self.assertEqual(provider2.api_key, "explicit-key")
                self.assertEqual(str(provider2.output_dir), tmpdir2)
                self.assertTrue(os.path.isdir(str(provider2.output_dir)))
            finally:
                try:
                    os.rmdir(tmpdir2)
                except OSError:
                    pass
        finally:
            # Restore original environment
            if original is None:
                os.environ.pop("MODELSLAB_API_KEY", None)
            else:
                os.environ["MODELSLAB_API_KEY"] = original
