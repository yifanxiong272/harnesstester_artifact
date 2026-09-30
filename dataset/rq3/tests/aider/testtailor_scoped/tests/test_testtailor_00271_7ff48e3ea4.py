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
        """Call diff_partial_update with an empty original (num_orig_lines == 0)
        and final=True so the branch that sets pct = 50 is exercised.
        """
        # empty original file
        lines_orig = []
        # one-line updated content (must include newline)
        lines_updated = ["new\n"]

        # call with final=True to force last_non_deleted = num_orig_lines (0)
        result = diff_partial_update(lines_orig, lines_updated, final=True, fname="foo.txt")

        # basic sanity checks on the output
        self.assertIsInstance(result, str)
        # file header should be present because we passed fname
        self.assertIn("--- foo.txt original", result)
        self.assertIn("+++ foo.txt updated", result)
        # the added line should appear in the unified diff
        self.assertIn("+new\n", result)
