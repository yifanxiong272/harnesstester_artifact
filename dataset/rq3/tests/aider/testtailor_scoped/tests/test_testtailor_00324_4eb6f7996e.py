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
        """Exercise tree_context with both single and multiple lines of interest."""
        fname = "example.py"
        code = (
            "def foo():\n"
            "    a = 1\n"
            "    b = 2\n"
            "    return a + b\n\n"
            "def bar():\n"
            "    pass\n"
        )

        # Multiple lines -> plural "lines" should be used
        out_multi = tree_context(fname, code, [2, 6])
        # Header should indicate plural and include the block marker
        self.assertIn("## See relevant lines below marked with █.", out_multi)
        # Filename should be present followed by a colon and newline
        self.assertIn(fname + ":\n", out_multi)
        # The block marker should appear somewhere in the formatted context
        self.assertIn("█", out_multi)

        # Single line -> singular "line" should be used
        out_single = tree_context(fname, code, [3])
        self.assertIn("## See relevant line below marked with █.", out_single)
        self.assertIn(fname + ":\n", out_single)
        self.assertIn("█", out_single)
