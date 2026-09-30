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
        """When final=True the function should treat the whole original file as non-deleted
        and therefore the diff should show deletions for lines that are missing from the
        updated version (i.e. we hit the branch where last_non_deleted = num_orig_lines).
        """
        lines_orig = ["keep\n", "also\n", "remove1\n", "remove2\n"]
        lines_updated = ["keep\n", "also\n"]

        out = diff_partial_update(lines_orig, lines_updated, final=True, fname="test.txt")

        # output should be fenced diff
        self.assertTrue(out.startswith("```diff\n"))

        # headers for the original/updated files should be present
        self.assertIn("--- test.txt original\n", out)
        self.assertIn("+++ test.txt updated\n", out)

        # because final=True we expect the deletions to be shown for the trailing lines
        self.assertIn("-remove1\n", out)
        self.assertIn("-remove2\n", out)
