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
        """Ensure lint_python_compile returns a LintResult with traceback text when compile fails."""
        fname = "test_file_for_lint.py"
        # Intentionally invalid Python to trigger a SyntaxError during compile()
        code = "def broken(:\n    pass\n"

        result = lint_python_compile(fname, code)

        # Should return a LintResult instance containing the formatted traceback text
        self.assertIsInstance(result, LintResult)
        self.assertIsInstance(result.text, str)
        # The traceback text should mention a SyntaxError and the provided filename
        self.assertIn("SyntaxError", result.text)
        self.assertIn(fname, result.text)

        # lines should be a list of non-negative integers (may be empty)
        self.assertIsInstance(result.lines, list)
        for ln in result.lines:
            self.assertIsInstance(ln, int)
            self.assertGreaterEqual(ln, 0)
