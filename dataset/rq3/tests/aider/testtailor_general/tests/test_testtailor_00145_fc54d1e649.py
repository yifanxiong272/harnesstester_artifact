import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.wholefile_func_coder')
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
        """When partial_response_content is set, render_incremental_response should return it immediately."""
        # Create instance without calling __init__ (which raises)
        coder = object.__new__(WholeFileFunctionCoder)
        coder.partial_response_content = "PARTIAL_CONTENT"

        # Should return the partial content regardless of final flag
        res1 = coder.render_incremental_response(final=False)
        res2 = coder.render_incremental_response(final=True)

        self.assertEqual(res1, "PARTIAL_CONTENT")
        self.assertEqual(res2, "PARTIAL_CONTENT")
