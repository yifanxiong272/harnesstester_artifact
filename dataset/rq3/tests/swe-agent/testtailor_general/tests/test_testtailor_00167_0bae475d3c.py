import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.utils.patch_formatter')
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
        """Trigger the branch where `last_stop` is not None so `n_omitted = start - last_stop` is executed."""
        # Instantiate the real PatchFormatter; read_method won't be used for this test
        pf = PatchFormatter("", lambda p: "")

        # Create a file with 6 lines
        text = "\n".join(f"line{i}" for i in range(1, 7))

        # Two non-overlapping hunks:
        # - First hunk: lines 1..2 (start=1, stop=3 -> stop is not inclusive)
        # - Second hunk: lines 4..5 (start=4, stop=6)
        # This ensures the loop runs twice and `last_stop` is not None on the second iteration.
        starts = [1, 4]
        stops = [3, 6]

        result = pf.format_file(text, starts, stops, linenos=True)

        # The omitted-lines marker between hunks should be present and equal to 1 line omitted
        self.assertIn("\n[1 lines omitted]\n", result)

        # Also check that line numbers from each hunk are present
        self.assertIn("     1: line1", result)
        self.assertIn("     4: line4", result)
