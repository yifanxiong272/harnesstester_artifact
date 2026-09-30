import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.algo.token_handler')
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
        """Test various model names for openai model detection covering both 'gpt' substring and regex paths."""
        # 'gpt' substring path should return the boolean True
        self.assertIs(ModelTypeValidator.is_openai_model("gpt-4"), True)
        self.assertIs(ModelTypeValidator.is_openai_model("my-gpt-model-v2"), True)

        # regex path: single digit o[1-9] with optional suffixes should be truthy (match object)
        res_o1 = ModelTypeValidator.is_openai_model("o1")
        self.assertTrue(bool(res_o1))
        res_o3_mini = ModelTypeValidator.is_openai_model("o3-mini")
        self.assertTrue(bool(res_o3_mini))
        res_o9_preview = ModelTypeValidator.is_openai_model("o9-preview")
        self.assertTrue(bool(res_o9_preview))

        # negative cases: digits outside 1-9, multi-digit, uppercase 'GPT' (case-sensitive), and unrelated names
        self.assertFalse(bool(ModelTypeValidator.is_openai_model("o0")))
        self.assertFalse(bool(ModelTypeValidator.is_openai_model("o10")))
        self.assertFalse(bool(ModelTypeValidator.is_openai_model("GPT")))
        self.assertFalse(bool(ModelTypeValidator.is_openai_model("bert-model")))
