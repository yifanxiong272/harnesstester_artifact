import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.linter')
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
        """basic_lint should return early (None) when filename_to_lang reports 'typescript'."""
        # Patch the filename_to_lang used by basic_lint by replacing it in the function's globals.
        orig_fn = basic_lint.__globals__.get("filename_to_lang", None)
        try:
            basic_lint.__globals__[
                "filename_to_lang"
            ] = lambda fname: "typescript"  # force the typescript branch
            # Call the function under test; it should return None (early return)
            result = basic_lint("example.ts", "some typescript code")
            self.assertIsNone(result, "basic_lint should return None for typescript files")
        finally:
            # Restore original if present
            if orig_fn is not None:
                basic_lint.__globals__["filename_to_lang"] = orig_fn
            else:
                # remove our injected name if there was no original
                basic_lint.__globals__.pop("filename_to_lang", None)
