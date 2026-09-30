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
        """Verify basic_lint queries filename_to_lang and returns early when no lang."""
        # Replace filename_to_lang used by basic_lint via its globals to avoid import-path issues
        orig = basic_lint.__globals__.get("filename_to_lang")
        called = {}

        def fake_filename_to_lang(fname):
            called["fname"] = fname
            return None  # force the early return branch

        basic_lint.__globals__["filename_to_lang"] = fake_filename_to_lang
        try:
            result = basic_lint("some_file.unknown", "print('hello')")
            # Function should return None when filename_to_lang returns falsy value
            self.assertIsNone(result)
            # Ensure filename_to_lang was called with the provided filename
            self.assertEqual(called.get("fname"), "some_file.unknown")
        finally:
            # Restore original
            if orig is None:
                basic_lint.__globals__.pop("filename_to_lang", None)
            else:
                basic_lint.__globals__["filename_to_lang"] = orig
