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
        """Ensure _get_hunk_lines computes starts/stops using source_start/source_length when original=True."""
        # Create a PatchFormatter (read_method can be a no-op since we will override _patch)
        pf = PatchFormatter(patch="", read_method=lambda p: "")

        # Create fake hunks that expose source_start and source_length
        class FakeHunk:
            def __init__(self, source_start, source_length):
                self.source_start = source_start
                self.source_length = source_length

        # Create a fake patch that is iterable over hunks and marked as modified
        class FakePatch:
            def __init__(self, path, hunks):
                self.path = path
                self.hunks = hunks
                self.is_modified_file = True

            def __iter__(self):
                return iter(self.hunks)

        # Two hunks: one that will be clamped to start=1, another with normal calculation
        hunk1 = FakeHunk(source_start=3, source_length=4)   # with context 5 -> start = max(1, 3-5) = 1, stop = 3+4+5 = 12
        hunk2 = FakeHunk(source_start=20, source_length=2)  # with context 5 -> start = 15, stop = 27

        fake_patch = FakePatch("some/file.py", [hunk1, hunk2])

        # Override the internal _patch with our fake patch list
        pf._patch = [fake_patch]

        # Call the target method with original=True
        result = pf._get_hunk_lines(original=True, context_length=5)

        expected_starts = [1, 15]
        expected_stops = [12, 27]
        self.assertIn("some/file.py", result)
        self.assertEqual(result["some/file.py"], (expected_starts, expected_stops))
