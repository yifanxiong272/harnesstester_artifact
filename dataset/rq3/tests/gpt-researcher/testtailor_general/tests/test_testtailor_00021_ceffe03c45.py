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
        """Test get_prompt_by_report_type returns the correct prompt for valid types
        and falls back (with a UserWarning) to the default prompt for invalid types.
        """
        # Minimal dummy PromptFamily with the expected attribute names
        class DummyPromptFamily:
            generate_report_prompt = "REPORT_PROMPT"
            generate_resource_report_prompt = "RESOURCE_PROMPT"

        # Pick a valid report type key from the project's mapping (should be the ResearchReport key)
        valid_report_type_key = list(report_type_mapping.keys())[0]

        # When passing the class itself, getattr should find the class attribute
        result_valid = get_prompt_by_report_type(valid_report_type_key, DummyPromptFamily)
        self.assertEqual(result_valid, "REPORT_PROMPT")

        # When passing an instance and an invalid report type, it should warn and return default
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            result_invalid = get_prompt_by_report_type("completely_invalid_type", DummyPromptFamily())
            # Should return the default (ResearchReport) prompt attribute value
            self.assertEqual(result_invalid, "REPORT_PROMPT")
            # A UserWarning should have been issued containing "Invalid report type"
            self.assertTrue(any(isinstance(w.message, Warning) or issubclass(w.category, UserWarning) for w in caught_warnings))
            self.assertTrue(any("Invalid report type" in str(w.message) for w in caught_warnings))
