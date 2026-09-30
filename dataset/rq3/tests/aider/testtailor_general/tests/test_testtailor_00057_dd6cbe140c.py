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
        """Ensure lint_python_compile returns a LintResult with traceback text and correct lines on syntax error."""
        # Provide a code string that will raise a SyntaxError at line 1
        fname = "bad.py"
        code = ")\n"

        result = lint_python_compile(fname, code)

        # Basic shape checks
        self.assertIsNotNone(result)
        self.assertTrue(hasattr(result, "text"))
        self.assertTrue(hasattr(result, "lines"))

        # The syntax error is on the first line, so lines should be [0]
        self.assertEqual(result.lines, [0])

        # The returned text should contain a SyntaxError and the supplied filename
        self.assertIn("SyntaxError", result.text)
        self.assertIn(fname, result.text)
