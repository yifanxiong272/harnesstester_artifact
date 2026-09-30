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
        """Image provider unavailable should leave image_provider as None and log a warning."""
        # Create a minimal cfg object enabling image generation
        cfg = type("Cfg", (), {})()
        cfg.IMAGE_GENERATION_ENABLED = True
        cfg.IMAGE_GENERATION_PROVIDER = "google"
        cfg.IMAGE_GENERATION_MODEL = None
        cfg.image_generation_max_images = 2

        # Minimal researcher object required by ImageGenerator
        researcher = type("R", (), {})()
        researcher.cfg = cfg
        researcher.verbose = False
        researcher.websocket = None
        researcher.add_costs = lambda *a, **k: None

        # Prepare a provider instance whose is_available() returns False
        provider_instance = MagicMock()
        provider_instance.is_available.return_value = False

        # Mock constructor that returns our provider_instance
        mock_constructor = MagicMock(return_value=provider_instance)

        # Patch the constructors in the module where ImageGenerator is defined using __import__
        module = __import__(ImageGenerator.__module__, fromlist=['ImageGeneratorProvider', 'ModelsLabImageGeneratorProvider'])
        setattr(module, "ImageGeneratorProvider", mock_constructor)
        setattr(module, "ModelsLabImageGeneratorProvider", mock_constructor)

        # Instantiate ImageGenerator which will call _init_provider and should hit the warning branch
        img_gen = ImageGenerator(researcher)

        # Since provider.is_available() returned False, image_provider should remain None
        self.assertIsNone(img_gen.image_provider)

        # Ensure the correct provider constructor was called (google path uses ImageGeneratorProvider with model_name)
        mock_constructor.assert_called_once_with(model_name=None)

        # And the provider's is_available() was checked
        provider_instance.is_available.assert_called_once()
