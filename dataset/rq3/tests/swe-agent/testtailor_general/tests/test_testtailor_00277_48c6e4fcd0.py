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
        """Trigger the branch that appends '[N lines below omitted]'."""
        # Prepare a text with 6 lines
        text = "\n".join([f"line{i}" for i in range(1, 7)])
        # Request a hunk that ends before the end of the file so there are lines below
        starts = [1]
        stops = [4]  # stop is not inclusive -> includes lines 1..3, leaving 3 lines, so omitted = 6 - 4 = 2

        # Create a minimal dummy self that provides _merge_intervals to the method
        class Dummy:
            pass

        d = Dummy()
        # Use identity merge (no merging needed for this test)
        d._merge_intervals = lambda s, t: (s, t)

        # Call the target method
        result = PatchFormatter.format_file(d, text, starts, stops, linenos=True)

        # Check that the "[... lines below omitted]" message was appended
        self.assertIn("[2 lines below omitted]", result)

        # Ensure the included lines are present with line numbers formatted as in the function
        self.assertIn(f"{1:6d}: line1", result)
        self.assertIn(f"{2:6d}: line2", result)
        self.assertIn(f"{3:6d}: line3", result)
