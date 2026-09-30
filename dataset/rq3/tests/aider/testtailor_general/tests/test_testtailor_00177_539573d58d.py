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
        """Test get_random_color produces deterministic hex color when random.random is mocked."""
        # Force hue to 0.0 which should produce a red at value=0.75:
        # HSV(0.0, 1, 0.75) -> RGB ~= (0.75, 0.0, 0.0) -> 0.75*255 = 191 -> 0xbf
        with patch("random.random", return_value=0.0):
            color = get_random_color()

        # Expect "#bf0000"
        self.assertEqual(color, "#bf0000")

        # Additional sanity checks on format
        self.assertTrue(color.startswith("#"))
        self.assertEqual(len(color), 7)
        # All characters after '#' should be valid hex digits
        int(color[1:], 16)  # will raise ValueError if not valid hex
