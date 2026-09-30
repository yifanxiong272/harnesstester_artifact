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
        """When get_parser raises an exception, basic_lint should print an error and return."""
        # Backup originals
        orig_get_parser = basic_lint.__globals__.get("get_parser")
        orig_filename_to_lang = basic_lint.__globals__.get("filename_to_lang")

        # Replace filename_to_lang to ensure we take the parser-loading branch
        basic_lint.__globals__["filename_to_lang"] = lambda fname: "python"

        # Replace get_parser to raise an exception to hit the except block
        def fake_get_parser(lang):
            raise Exception("boom!")
        basic_lint.__globals__["get_parser"] = fake_get_parser

        try:
            with patch("builtins.print") as mock_print:
                result = basic_lint("file.py", "print('hello')")

                # Function should return None after printing the error
                self.assertIsNone(result)

                # Ensure print was called with the expected message
                mock_print.assert_called_once()
                printed = mock_print.call_args[0][0]
                self.assertIn("Unable to load parser", printed)
                self.assertIn("boom", printed)
        finally:
            # Restore originals
            if orig_get_parser is not None:
                basic_lint.__globals__["get_parser"] = orig_get_parser
            else:
                del basic_lint.__globals__["get_parser"]

            if orig_filename_to_lang is not None:
                basic_lint.__globals__["filename_to_lang"] = orig_filename_to_lang
            else:
                del basic_lint.__globals__["filename_to_lang"]
