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
        """Ensure DSCoderFeedback.val_and_update_init_dict calls the parent validator and processes new fields."""
        data = {
            "final_decision": "false",  # should be converted to False by parent
            "execution": "print('exec')",
            "return_checking": "returns ok",
            "code": "def foo(): pass",
            "requires_documentation_search": "true",  # should be converted to True by DSCoderFeedback validator
            "error_message": "an error occurred",  # valid string
        }

        updated = DSCoderFeedback.val_and_update_init_dict(data.copy())

        # Parent conversion: final_decision string -> boolean False
        self.assertIsInstance(updated["final_decision"], bool)
        self.assertFalse(updated["final_decision"])

        # Fields passed through unchanged (strings remain strings)
        self.assertEqual(updated["execution"], data["execution"])
        self.assertEqual(updated["return_checking"], data["return_checking"])
        self.assertEqual(updated["code"], data["code"])

        # DSCoderFeedback-specific conversion: requires_documentation_search string -> boolean True
        self.assertIsInstance(updated["requires_documentation_search"], bool)
        self.assertTrue(updated["requires_documentation_search"])

        # error_message preserved
        self.assertEqual(updated["error_message"], data["error_message"])
