import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.utils.costs')
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
        """Ensure _extract_anthropic_usage falls back to usage_metadata and converts token counts to ints."""
        # Access the internal helper from the imported calculate_llm_cost's globals
        extract = calculate_llm_cost.__globals__["_extract_anthropic_usage"]

        # response_metadata does not include "usage" so the function should use usage_metadata
        result = extract(
            response_metadata={"model": "claude-test-4-0"},
            usage_metadata={"input_tokens": "42", "output_tokens": "7"},
        )

        self.assertEqual(result, {"input_tokens": 42, "output_tokens": 7})
