import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.diffs')
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
        """When the original file has zero lines, the function should run the branch
        that sets pct = 50 (num_orig_lines == 0) and produce a valid unified diff output."""
        lines_orig = []
        lines_updated = ["new line\n"]

        # Use final=True so we don't return early due to find_last_non_deleted being None
        result = diff_partial_update(lines_orig, lines_updated, final=True, fname="file.txt")

        # Should produce a diff block with headers and the added line
        self.assertTrue(result.startswith("```diff\n"))
        self.assertIn("--- file.txt original", result)
        self.assertIn("+++ file.txt updated", result)
        self.assertIn("+new line", result)
        self.assertTrue(result.rstrip().endswith("```"))
