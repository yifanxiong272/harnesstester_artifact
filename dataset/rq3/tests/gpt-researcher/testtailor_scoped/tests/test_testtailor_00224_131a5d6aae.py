import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.prompts')
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
        """Ensure get_prompt_family accepts a PromptFamilyEnum instance and returns the proper PromptFamily instance."""
        # Use a simple mock config object
        config = MagicMock(name="Config")

        # Call with an enum instance so the code path `prompt_family_name = prompt_family_name.value` is taken
        prompt_family = get_prompt_family(PromptFamilyEnum.Default, config)

        # Verify we got an instance of PromptFamily (constructed with our config)
        self.assertIsInstance(prompt_family, PromptFamily)
        self.assertIs(prompt_family.cfg, config)
