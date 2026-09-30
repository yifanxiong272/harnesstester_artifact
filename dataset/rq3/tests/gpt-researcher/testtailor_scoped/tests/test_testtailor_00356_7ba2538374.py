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
        """Verify ImageGenerator.is_enabled() for various image_provider states."""
        # Create a minimal cfg that disables auto provider initialization
        cfg = type('C', (), {
            'IMAGE_GENERATION_ENABLED': False,
            'image_generation_max_images': 3,
            'fast_llm_model': 'test-model',
            'fast_llm_provider': 'test-provider',
            'llm_kwargs': {}
        })()

        researcher = MagicMock()
        researcher.cfg = cfg
        researcher.verbose = False
        researcher.websocket = None

        # Initialize generator (will not set a provider because IMAGE_GENERATION_ENABLED is False)
        gen = ImageGenerator(researcher)

        # Case 1: no provider set
        gen.image_provider = None
        self.assertFalse(gen.is_enabled(), "Expected is_enabled() to be False when image_provider is None")

        # Case 2: provider exists but reports not available
        provider_mock = MagicMock()
        provider_mock.is_available.return_value = False
        gen.image_provider = provider_mock
        self.assertFalse(gen.is_enabled(), "Expected is_enabled() to be False when provider.is_available() is False")

        # Case 3: provider exists and is available
        provider_mock.is_available.return_value = True
        self.assertTrue(gen.is_enabled(), "Expected is_enabled() to be True when provider.is_available() is True")
