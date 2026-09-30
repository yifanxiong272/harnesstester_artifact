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
        """Ensure format_file emits the 'lines above omitted' message when the first hunk
        does not start at line 1 (starts[0] > 1)."""
        # Create an instance without running __init__
        pf = PatchFormatter.__new__(PatchFormatter)
        # Attach the static method to the instance as a plain function to avoid implicit binding issues
        pf._merge_intervals = PatchFormatter._merge_intervals

        # Prepare a sample file with 5 lines (splitlines() will produce 5 elements)
        text = "\n".join(f"line{i}" for i in range(1, 6)) + "\n"

        # Request a hunk that starts at line 3 (so lines 1-2 are "above" and should be reported omitted)
        starts = [3]
        stops = [5]  # stop is not inclusive -> lines 3 and 4 should be returned

        result = pf.format_file(text, starts, stops, linenos=True)

        expected_hunk = "\n".join([f"{i:6d}: line{i}" for i in (3, 4)])
        expected = f"[{starts[0] - 1} lines above omitted]\n{expected_hunk}"

        self.assertEqual(result, expected)
