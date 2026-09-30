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
        """Ensure overlapping intervals extend the previous interval's stop (executes the merge assignment)."""
        # Case where a later interval overlaps and extends the previous one
        starts = [1, 5]
        stops = [10, 15]
        merged_starts, merged_stops = PatchFormatter._merge_intervals(starts, stops)
        self.assertEqual(merged_starts, [1])
        self.assertEqual(merged_stops, [15])

        # Case with multiple hunks where the last hunk merges into the previous one
        starts2 = [1, 4, 6]
        stops2 = [3, 10, 8]
        ms, mt = PatchFormatter._merge_intervals(starts2, stops2)
        self.assertEqual(ms, [1, 4])
        self.assertEqual(mt, [3, 10])
