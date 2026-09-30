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
        """Verify the is_anthropic_model behavior for various model name inputs."""
        # exact match
        self.assertTrue(ModelTypeValidator.is_anthropic_model("claude"))
        # substring occurrences
        self.assertTrue(ModelTypeValidator.is_anthropic_model("anthropic-claude-v1"))
        self.assertTrue(ModelTypeValidator.is_anthropic_model("my_claude_model"))
        # leading/trailing whitespace still contains substring
        self.assertTrue(ModelTypeValidator.is_anthropic_model(" claude "))
        # case-sensitivity: should be False because check is case-sensitive
        self.assertFalse(ModelTypeValidator.is_anthropic_model("Claude"))
        # unrelated names
        self.assertFalse(ModelTypeValidator.is_anthropic_model("openai-gpt"))
        # empty string should not match
        self.assertFalse(ModelTypeValidator.is_anthropic_model(""))
