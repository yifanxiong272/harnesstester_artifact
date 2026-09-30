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
        """Ensure get_prompt_family warns and returns default when given an invalid name."""
        # Create a dummy PromptFamily to avoid constructor signature mismatches
        class DummyPromptFamily:
            def __init__(self, *args, **kwargs):
                self.created = True

        # Replace the PromptFamily in get_prompt_family's globals with our dummy, then restore after test
        gf_globals = get_prompt_family.__globals__
        original_prompt_family = gf_globals.get("PromptFamily")
        try:
            gf_globals["PromptFamily"] = DummyPromptFamily

            with warnings.catch_warnings(record=True) as caught_warnings:
                warnings.simplefilter("always")
                cfg = MagicMock()
                result = get_prompt_family("this_prompt_family_does_not_exist", cfg)

                # Verify a UserWarning was emitted with expected content
                self.assertTrue(len(caught_warnings) >= 1)
                last_warning = caught_warnings[-1]
                self.assertTrue(issubclass(last_warning.category, UserWarning))
                self.assertIn("Invalid prompt family: this_prompt_family_does_not_exist", str(last_warning.message))

                # Ensure the mapping keys are mentioned in the warning message
                mapping = gf_globals.get("prompt_family_mapping", {})
                for key in mapping.keys():
                    self.assertIn(key, str(last_warning.message))

                # Verify the function returned an instance of the default PromptFamily (our dummy)
                self.assertIsInstance(result, DummyPromptFamily)
        finally:
            # restore original
            gf_globals["PromptFamily"] = original_prompt_family
