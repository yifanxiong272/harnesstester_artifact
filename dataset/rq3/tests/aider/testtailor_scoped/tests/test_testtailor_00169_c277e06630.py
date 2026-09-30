import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.editblock_func_coder')
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
        # Create a minimal dummy object to serve as `self` for the unbound method call.
        dummy = type("Dummy", (), {})()
        # Set partial_response_function_call so the method reads the "name" key.
        dummy.partial_response_function_call = {"name": "bad"}
        # Calling the unbound method should raise the expected ValueError for unknown name.
        with self.assertRaisesRegex(
            ValueError, 'Unknown function_call name="bad", use name="replace_lines"'
        ):
            EditBlockFunctionCoder._update_files(dummy)
