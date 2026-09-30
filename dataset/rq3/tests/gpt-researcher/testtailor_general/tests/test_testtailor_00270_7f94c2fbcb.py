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
        """Ensure anthropic usage is extracted from usage_metadata when response_metadata.usage is empty"""
        class UsageObj:
            def model_dump(self):
                return {"input_tokens": 100, "output_tokens": 50}

        cost = calculate_llm_cost(
            llm_provider="anthropic",
            model="claude-opus-4-7",
            input_content="ignored",
            output_content="ignored",
            response_metadata={"usage": {}},
            usage_metadata=UsageObj(),
        )

        self.assertAlmostEqual(cost, 0.00175)
