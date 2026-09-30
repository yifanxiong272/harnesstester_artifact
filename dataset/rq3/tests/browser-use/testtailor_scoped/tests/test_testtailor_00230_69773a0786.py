import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.llm.anthropic.chat')
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
        """Verify _is_adaptive_thinking_only_model detects claude-fable-5 and claude-mythos-5 (case-insensitive)
        and does not trigger for unrelated model names.
        """
        # Create instance without running __init__ to avoid requiring other constructor args
        inst = object.__new__(ChatAnthropic)

        # Mixed-case should be handled (lowercased in method)
        inst.model = "Claude-Fable-5"
        self.assertTrue(inst._is_adaptive_thinking_only_model())

        # Substring anywhere in the name should match
        inst.model = "my-custom-claude-mythos-5-version"
        self.assertTrue(inst._is_adaptive_thinking_only_model())

        # Similar but not matching substring should be False
        inst.model = "claude-fable-50"  # still contains 'claude-fable-5' -> should be True
        self.assertTrue(inst._is_adaptive_thinking_only_model())

        # Completely different model name should be False
        inst.model = "some-other-model"
        self.assertFalse(inst._is_adaptive_thinking_only_model())
