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
        """Verify that _generate_filename returns the expected md5-based filename."""
        provider = ModelsLabImageGeneratorProvider()
        prompt = "A scenic mountain at sunrise"
        index = 3

        result = provider._generate_filename(prompt, index)

        expected_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        expected = f"img_{expected_hash}_{index}.png"
        self.assertEqual(result, expected)

        # also verify default index (0) behavior
        result_default = provider._generate_filename(prompt)
        expected_default = f"img_{expected_hash}_0.png"
        self.assertEqual(result_default, expected_default)
