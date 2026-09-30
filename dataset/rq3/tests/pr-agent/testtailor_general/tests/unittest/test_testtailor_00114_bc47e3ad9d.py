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
        """Verify that models containing the substring 'claude' are detected (case-sensitive)."""
        # Direct top-level function (if available)
        try:
            func = is_anthropic_model
        except NameError:
            func = None

        # Class static method
        cls_func = ModelTypeValidator.is_anthropic_model

        # Positive cases: exact and containing substring
        if func:
            self.assertTrue(func("claude"))
            self.assertTrue(func("claude-v1"))
            self.assertTrue(func("anthropic-claude-xl"))
            self.assertTrue(func("notclauder"))  # substring present

        self.assertTrue(cls_func("mini-claude"))
        self.assertTrue(cls_func("something-claude-something"))

        # Negative cases: case sensitivity and unrelated names
        if func:
            self.assertFalse(func("Claude"))  # different case -> should be False
            self.assertFalse(func("CLAUDE"))
            self.assertFalse(func(""))
            self.assertFalse(func("gpt-4"))

        self.assertFalse(cls_func("Claude"))
        self.assertFalse(cls_func("gpt-4"))
        self.assertFalse(cls_func(""))
