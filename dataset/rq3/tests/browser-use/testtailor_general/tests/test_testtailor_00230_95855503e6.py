import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.browser.video_recorder')
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
        """Ensure VideoRecorderService.__init__ sets attributes and computes padded_size correctly."""
        # Arrange
        out_path = Path("output_test_video.mp4")
        size = ViewportSize(width=123, height=87)
        framerate = 30

        # Act
        recorder = VideoRecorderService(output_path=out_path, size=size, framerate=framerate)

        # Assert basic attribute assignments
        self.assertEqual(recorder.output_path, out_path)
        self.assertIs(recorder.size, size)  # same object passed through
        self.assertEqual(recorder.framerate, framerate)

        # Assert internal state defaults
        self.assertIsNone(recorder._writer)
        self.assertFalse(recorder._is_active)

        # Assert padded size is computed to the next multiple of 16
        # width: ceil(123/16) = 8 -> 8*16 = 128
        # height: ceil(87/16) = 6 -> 6*16 = 96
        self.assertEqual(recorder.padded_size['width'], 128)
        self.assertEqual(recorder.padded_size['height'], 96)
