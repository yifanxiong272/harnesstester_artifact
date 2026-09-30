import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.memory.condenser.impl.llm_summarizing_condenser')
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
        """Assert that constructing LLMSummarizingCondenser with a non-positive max_size raises the specific ValueError about max_size being non-positive.

        We inject a keep_first object that deliberately returns False for both
        comparisons used in the constructor (>= and <) so the constructor
        proceeds to the max_size check and raises the intended error.
        """
        mock_llm = MagicMock(spec=LLM)

        class KeepFirstProxy:
            def __ge__(self, other):
                # Ensure "keep_first >= max_size // 2" evaluates to False
                return False

            def __lt__(self, other):
                # Ensure "keep_first < 0" evaluates to False
                return False

        with self.assertRaises(ValueError) as cm:
            LLMSummarizingCondenser(llm=mock_llm, max_size=0, keep_first=KeepFirstProxy())

        self.assertIn("max_size (0) cannot be non-positive", str(cm.exception))
