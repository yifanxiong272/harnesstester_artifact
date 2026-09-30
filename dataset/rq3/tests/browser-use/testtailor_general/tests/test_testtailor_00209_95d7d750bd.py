import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.dom.serializer.paint_order')
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
        """Verify Rect.area returns width * height for normal and degenerate rectangles."""
        # normal rectangle
        r = Rect(x1=1.5, y1=2.0, x2=4.0, y2=6.5)
        expected = (4.0 - 1.5) * (6.5 - 2.0)  # 2.5 * 4.5 = 11.25
        self.assertAlmostEqual(r.area(), expected)

        # zero width
        r_zero_width = Rect(x1=0.0, y1=0.0, x2=0.0, y2=5.0)
        self.assertAlmostEqual(r_zero_width.area(), 0.0)

        # zero height
        r_zero_height = Rect(x1=-2.0, y1=3.0, x2=2.0, y2=3.0)
        self.assertAlmostEqual(r_zero_height.area(), 0.0)
