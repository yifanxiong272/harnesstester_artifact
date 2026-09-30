import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.memory.condenser.impl.llm_attention_condenser')
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
        """Ensure LLMAttentionCondenser raises if keep_first is >= half of max_size."""
        max_size = 10
        keep_first = 5  # equal to max_size // 2, should be invalid

        expected_msg = f'keep_first ({keep_first}) must be less than half of max_size ({max_size})'

        with self.assertRaises(ValueError) as cm:
            # The constructor checks keep_first before using the llm argument,
            # so we can safely pass None for llm.
            LLMAttentionCondenser(llm=None, max_size=max_size, keep_first=keep_first)

        self.assertEqual(str(cm.exception), expected_msg)
