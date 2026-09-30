import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.repomap')
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
        """Test deterministic outputs of get_random_color by patching random.random."""
        # Hue = 0.0 -> red at value=0.75 -> 0.75*255 = 191 -> hex 'bf'
        with patch("random.random", return_value=0.0):
            self.assertEqual(get_random_color(), "#bf0000")

        # Hue = 1/3 -> green
        with patch("random.random", return_value=1.0 / 3.0):
            self.assertEqual(get_random_color(), "#00bf00")

        # Hue = 2/3 -> blue
        with patch("random.random", return_value=2.0 / 3.0):
            self.assertEqual(get_random_color(), "#0000bf")

        # Additional checks for formatting and valid hex output
        with patch("random.random", return_value=0.125):
            color = get_random_color()
            self.assertTrue(color.startswith("#"))
            self.assertEqual(len(color), 7)  # # + 6 hex digits
            # Ensure the hex part is parseable
            int(color[1:], 16)
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            for v in (r, g, b):
                self.assertGreaterEqual(v, 0)
                self.assertLessEqual(v, 255)
