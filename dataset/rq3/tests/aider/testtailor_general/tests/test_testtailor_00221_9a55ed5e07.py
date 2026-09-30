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
        """Calling _update_files with an unknown function_call name raises ValueError"""
        coder = object.__new__(EditBlockFunctionCoder)
        coder.partial_response_function_call = {"name": "not_replace_lines"}

        with self.assertRaisesRegex(
            ValueError, 'Unknown function_call name="not_replace_lines", use name="replace_lines"'
        ):
            coder._update_files()
