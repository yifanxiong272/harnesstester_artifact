import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.actions.utils')
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
        """Ensure model name is case-insensitive and correct cost applied."""
        prompt_tokens = 250
        completion_tokens = 750
        model = "GPT-4"  # mixed/upper case to exercise model.lower()
        cost = calculate_cost(prompt_tokens, completion_tokens, model)
        expected = ((prompt_tokens + completion_tokens) / 1000) * 0.03  # gpt-4 cost per 1k tokens
        self.assertAlmostEqual(cost, expected, places=9)
