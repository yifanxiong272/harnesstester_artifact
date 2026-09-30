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
        """Verify that basic_lint calls filename_to_lang and returns early when it is falsy."""
        fname = "example.txt"
        code = "print('hello')"

        # Replace filename_to_lang in basic_lint's globals with a fake that records the argument
        original_fn = basic_lint.__globals__.get("filename_to_lang")
        called = {}

        def fake_filename_to_lang(arg):
            called["arg"] = arg
            return None  # Force the early return path in basic_lint

        basic_lint.__globals__["filename_to_lang"] = fake_filename_to_lang
        try:
            result = basic_lint(fname, code)
            # When filename_to_lang returns falsy, basic_lint should return None
            self.assertIsNone(result)
            # Ensure our fake was called with the filename we passed
            self.assertIn("arg", called)
            self.assertEqual(called["arg"], fname)
        finally:
            # Restore original function to avoid side effects on other tests
            basic_lint.__globals__["filename_to_lang"] = original_fn
