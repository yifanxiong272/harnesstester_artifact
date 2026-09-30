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
        """When partial_response_content is set, render_incremental_response should return it directly."""
        orig_init = EditBlockFunctionCoder.__init__
        try:
            # Bypass the real __init__ which raises RuntimeError
            EditBlockFunctionCoder.__init__ = lambda self, *a, **k: None

            coder = EditBlockFunctionCoder("list")

            # set a truthy partial response and verify it is returned as-is
            partial = {"progress": 42, "message": "still working"}
            coder.partial_response_content = partial

            result = coder.render_incremental_response(final=False)
            self.assertIs(result, partial)
            self.assertEqual(result, {"progress": 42, "message": "still working"})
        finally:
            EditBlockFunctionCoder.__init__ = orig_init
