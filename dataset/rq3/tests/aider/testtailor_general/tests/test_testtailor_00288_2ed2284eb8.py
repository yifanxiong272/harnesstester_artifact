import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.waiting')
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
        """Verify _next_frame returns the current frame and advances (including wrap-around)
        and that the class variable last_frame_idx is updated."""
        spinner = Spinner("testing")

        # Provide a simple predictable frames list and set a known starting index
        spinner.frames = ["frame0", "frame1", "frame2"]
        spinner.frame_idx = 1
        Spinner.last_frame_idx = 999  # ensure it gets overwritten

        # Call _next_frame and verify behavior (returns current frame, advances index)
        returned = spinner._next_frame()
        self.assertEqual(returned, "frame1")
        self.assertEqual(spinner.frame_idx, 2)
        self.assertEqual(Spinner.last_frame_idx, 2)

        # Now test wrap-around from last index to zero
        spinner.frame_idx = 2
        returned = spinner._next_frame()
        self.assertEqual(returned, "frame2")
        self.assertEqual(spinner.frame_idx, 0)
        self.assertEqual(Spinner.last_frame_idx, 0)
