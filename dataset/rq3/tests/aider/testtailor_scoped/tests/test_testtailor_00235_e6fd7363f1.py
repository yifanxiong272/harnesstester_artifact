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
        """Verify _next_frame returns the current frame and advances both instance and class indices, including wrap-around."""
        # Create a Spinner instance (constructor behavior is irrelevant for this test)
        spinner = Spinner("testing")

        # Inject a small predictable frame sequence and set the frame index to the last element
        spinner.frames = ["frame0", "frame1", "frame2"]
        spinner.frame_idx = 2
        Spinner.last_frame_idx = -1  # ensure class var changes

        # Call _next_frame and verify returned frame is the one at the original index
        returned = spinner._next_frame()
        self.assertEqual(returned, "frame2")

        # After advancing, the instance index should wrap to 0 and the class var updated
        self.assertEqual(spinner.frame_idx, 0)
        self.assertEqual(Spinner.last_frame_idx, 0)

        # Call again to ensure normal advancement from wrapped state
        returned2 = spinner._next_frame()
        self.assertEqual(returned2, "frame0")
        self.assertEqual(spinner.frame_idx, 1)
        self.assertEqual(Spinner.last_frame_idx, 1)
