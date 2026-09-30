import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.memory.condenser.impl.structured_summary_condenser')
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
        """Ensure StructuredSummaryCondenser raises the max_size non-positive error.

        The constructor checks keep_first against max_size//2 and whether keep_first is negative
        before checking max_size < 1. To reach the max_size check for a non-positive value
        we provide a keep_first object whose comparison operators return False so the earlier
        checks don't raise, allowing the max_size < 1 branch to execute.
        """
        # A dummy object that will make both comparisons with integers evaluate to False.
        class NonComparable:
            def __ge__(self, other):
                return False

            def __lt__(self, other):
                return False

        mock_llm = MagicMock(spec=LLM)
        # The function-calling check happens after the size checks, so its value doesn't matter here.
        mock_llm.is_function_calling_active.return_value = True

        with self.assertRaises(ValueError) as cm:
            StructuredSummaryCondenser(llm=mock_llm, max_size=0, keep_first=NonComparable())

        self.assertIn('max_size (0) cannot be non-positive', str(cm.exception))
