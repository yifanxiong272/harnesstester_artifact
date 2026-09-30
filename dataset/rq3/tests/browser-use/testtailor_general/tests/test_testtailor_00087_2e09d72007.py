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
        """Verify _get_padded_size pads width/height up to the nearest multiple of macro_block_size."""
        # Non-multiple sizes with default macro_block_size (16)
        size = ViewportSize(width=1025, height=767)
        padded = _get_padded_size(size)  # uses default macro_block_size=16
        # 1025 -> ceil(1025/16)=65 * 16 = 1040
        # 767  -> ceil(767/16)=48  * 16 = 768
        self.assertEqual(padded.width, 1040)
        self.assertEqual(padded.height, 768)
        # Ensure original size object was not mutated
        self.assertEqual(size.width, 1025)
        self.assertEqual(size.height, 767)

        # Exact multiples should remain unchanged
        size2 = ViewportSize(width=1280, height=720)
        padded2 = _get_padded_size(size2, macro_block_size=16)
        self.assertEqual(padded2.width, 1280)
        self.assertEqual(padded2.height, 720)

        # Zero dimensions remain zero
        size3 = ViewportSize(width=0, height=0)
        padded3 = _get_padded_size(size3, macro_block_size=16)
        self.assertEqual(padded3.width, 0)
        self.assertEqual(padded3.height, 0)

        # Different macro_block_size
        size4 = ViewportSize(width=15, height=17)
        padded4 = _get_padded_size(size4, macro_block_size=8)
        # 15 -> ceil(15/8)=2 * 8 = 16
        # 17 -> ceil(17/8)=3 * 8 = 24
        self.assertEqual(padded4.width, 16)
        self.assertEqual(padded4.height, 24)
