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
        """_generate_filename produces deterministic filenames using MD5(prompt)[:8] and index."""
        prompt = "A serene landscape with mountains"
        provider = ModelsLabImageGeneratorProvider()

        # generate filenames for index 0 and 2
        fname0 = provider._generate_filename(prompt, 0)
        fname2 = provider._generate_filename(prompt, 2)

        # compute expected hashes using hashlib
        import hashlib

        expected_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        expected0 = f"img_{expected_hash}_0.png"
        expected2 = f"img_{expected_hash}_2.png"

        self.assertEqual(fname0, expected0)
        self.assertEqual(fname2, expected2)

        # different prompt should produce a different hash segment
        other_prompt = "A bustling city at night"
        other_fname = provider._generate_filename(other_prompt, 0)
        expected_other_hash = hashlib.md5(other_prompt.encode()).hexdigest()[:8]
        self.assertEqual(other_fname, f"img_{expected_other_hash}_0.png")

        # basic format checks
        self.assertTrue(fname0.startswith("img_"))
        self.assertTrue(fname0.endswith(".png"))
        parts = fname0.split("_")
        # parts: ["img", "<hash>", "<index>.png"]
        self.assertEqual(parts[1], expected_hash)
        self.assertTrue(parts[2].endswith(".png"))
