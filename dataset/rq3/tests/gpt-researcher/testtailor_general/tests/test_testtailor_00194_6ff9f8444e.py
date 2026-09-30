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
        """Ensure ImageGenerator uses ImageGeneratorProvider when provider is not 'modelslab'."""
        # Prepare a mock provider that reports available
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True

        # Determine the module where ImageGenerator is defined so we can patch the provider name there
        module_name = ImageGenerator.__module__
        module = __import__(module_name, fromlist=['*'])

        # Use a SimpleNamespace for cfg
        SimpleNamespace = __import__('types').SimpleNamespace
        cfg = SimpleNamespace(
            IMAGE_GENERATION_ENABLED=True,
            IMAGE_GENERATION_PROVIDER='google',  # not 'modelslab' -> triggers ImageGeneratorProvider branch
            IMAGE_GENERATION_MODEL='test-model',
            image_generation_max_images=2,
            image_generation_style='dark',
            fast_llm_model='fast-model',
            fast_llm_provider='openai',
            llm_kwargs={},
        )

        researcher = MagicMock()
        researcher.cfg = cfg
        researcher.verbose = False
        researcher.websocket = None
        researcher.add_costs = lambda *a, **k: None

        # Patch the ImageGeneratorProvider symbol in the ImageGenerator's module to return our mock_provider
        with patch.object(module, 'ImageGeneratorProvider', return_value=mock_provider, create=True) as mock_imgprov:
            imggen = ImageGenerator(researcher)

            # Verify ImageGeneratorProvider was called with the model_name argument
            mock_imgprov.assert_called_once_with(model_name='test-model')
            # Confirm the image provider was set on the ImageGenerator instance
            self.assertIs(imggen.image_provider, mock_provider)
