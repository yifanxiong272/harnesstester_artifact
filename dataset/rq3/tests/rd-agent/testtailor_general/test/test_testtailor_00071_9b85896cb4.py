import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.CoSTEER.evaluators')
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
        """Should raise ValueError when 'final_decision' is missing from input dict."""
        data = {
            "execution": "some execution feedback",
            "return_checking": None,
            "code": "generated code"
        }
        with self.assertRaises(ValueError) as cm:
            CoSTEERSingleFeedback.val_and_update_init_dict(data)
        self.assertEqual(str(cm.exception), "'final_decision' is required")
