import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.skills.image_generator')
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
        """Ensure ModelsLabImageGeneratorProvider is constructed when provider_name == 'modelslab'."""
        # Prepare a minimal config that enables image generation and selects modelslab
        cfg = type("Cfg", (), {})()
        cfg.IMAGE_GENERATION_ENABLED = True
        cfg.IMAGE_GENERATION_PROVIDER = "modelslab"
        cfg.IMAGE_GENERATION_MODEL = "ml-model-1"
        # Attributes referenced by ImageGenerator but not used during init
        cfg.image_generation_max_images = 2

        # Minimal researcher stub
        researcher = type("R", (), {})()
        researcher.cfg = cfg
        researcher.verbose = False
        researcher.websocket = None

        # Locate the module where ImageGenerator is defined and patch the provider there
        import sys
        module = sys.modules.get(ImageGenerator.__module__)
        # Sanity check: the module should be loaded
        self.assertIsNotNone(module, f"Module for ImageGenerator not found: {ImageGenerator.__module__}")

        with patch.object(module, 'ModelsLabImageGeneratorProvider') as mock_models_lab:
            # Prepare the provider instance mock to appear available
            mock_provider_instance = MagicMock()
            mock_provider_instance.is_available.return_value = True
            mock_models_lab.return_value = mock_provider_instance

            # Instantiate the ImageGenerator (calls _init_provider in __init__)
            img_gen = ImageGenerator(researcher)

            # Verify the ModelsLab provider was constructed with the correct model_id
            mock_models_lab.assert_called_once_with(model_id="ml-model-1")

            # Verify the image_provider on the instance was set to the provider instance
            self.assertIs(img_gen.image_provider, mock_provider_instance)
