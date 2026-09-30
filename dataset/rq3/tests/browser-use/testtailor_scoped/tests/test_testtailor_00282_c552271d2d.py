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
        """Test _requires_auto_tool_choice reads self.name.lower() and branches correctly."""
        # Instance with model name containing 'claude-fable-5' should return True regardless of thinking
        inst = object.__new__(ChatAnthropic)
        inst.model = "Claude-Fable-5"
        inst.thinking = None
        self.assertTrue(inst._requires_auto_tool_choice())

        # Instance with model name containing 'claude-mythos-5' should also return True
        inst2 = object.__new__(ChatAnthropic)
        inst2.model = "org/claude-mythos-5-alpha"
        inst2.thinking = {'type': 'disabled'}
        self.assertTrue(inst2._requires_auto_tool_choice())

        # Model that does not match and thinking is None -> False
        inst3 = object.__new__(ChatAnthropic)
        inst3.model = "some-other-model"
        inst3.thinking = None
        self.assertFalse(inst3._requires_auto_tool_choice())

        # Model that does not match and thinking type is 'disabled' -> False
        inst4 = object.__new__(ChatAnthropic)
        inst4.model = "some-other-model"
        inst4.thinking = {'type': 'disabled'}
        self.assertFalse(inst4._requires_auto_tool_choice())

        # Model that does not match and thinking type is not 'disabled' -> True
        inst5 = object.__new__(ChatAnthropic)
        inst5.model = "some-other-model"
        inst5.thinking = {'type': 'enabled'}
        self.assertTrue(inst5._requires_auto_tool_choice())
