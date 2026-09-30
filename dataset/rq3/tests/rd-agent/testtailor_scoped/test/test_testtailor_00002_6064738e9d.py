import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.data_science.pipeline.eval')
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
        """Ensure CoSTEERSingleFeedback validation is invoked and string booleans are converted."""
        # Prepare input data that requires parent validation and also DSCoder-specific fields
        data = {
            "final_decision": "true",  # parent should convert this to boolean True
            "execution": "ran successfully",
            "return_checking": None,
            "code": "print('hello')",
            "requires_documentation_search": "True",  # DSCoderFeedback should convert this to True
            "error_message": "some error",
        }

        # Call the DSCoderFeedback validator which internally calls CoSTEERSingleFeedback.val_and_update_init_dict
        updated = DSCoderFeedback.val_and_update_init_dict(dict(data))

        # Assertions: types and converted values
        self.assertIsInstance(updated, dict)
        self.assertIs(updated["final_decision"], True)
        self.assertIs(updated["requires_documentation_search"], True)
        self.assertEqual(updated["error_message"], "some error")
        self.assertEqual(updated["execution"], "ran successfully")
        self.assertEqual(updated["code"], "print('hello')")
