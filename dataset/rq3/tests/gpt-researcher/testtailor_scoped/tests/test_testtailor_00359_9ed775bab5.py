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
        """Verify that the generated filename uses the first 8 chars of the MD5 prompt hash and the index."""
        provider = ImageGeneratorProvider()
        prompt = "A detailed diagram of neural network architecture"
        index = 3

        # Call the method under test
        filename = provider._generate_image_filename(prompt, index)

        # Compute expected filename using the same hashing logic
        expected_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        expected_filename = f"img_{expected_hash}_{index}.png"

        self.assertEqual(filename, expected_filename)

        # Also test default index (should default to 0)
        default_filename = provider._generate_image_filename(prompt)
        expected_default = f"img_{expected_hash}_0.png"
        self.assertEqual(default_filename, expected_default)
