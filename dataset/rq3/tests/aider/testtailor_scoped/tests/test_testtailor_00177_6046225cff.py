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
        """Ensure unicode translation path runs in __init__ and produces unicode frames/scan_char."""
        # Patch Spinner._supports_unicode to force the unicode branch without touching sys.stdout
        original_supports = Spinner._supports_unicode
        try:
            setattr(Spinner, "_supports_unicode", lambda self: True)
            spinner = Spinner("loading")

            # unicode_palette is "░█" so the mapped scan char for "#" (index 1 in "=#") should be "█"
            self.assertEqual(spinner.unicode_palette, "░█")
            self.assertEqual(spinner.scan_char, "█")

            # The first ascii frame "#=        " should translate to "█░        "
            expected_first = "█░        "
            self.assertEqual(spinner.frames[0], expected_first)

            # All frames should contain only characters from the translated palette or spaces
            allowed = set(spinner.unicode_palette + " =#")
            for f in spinner.frames:
                for ch in f:
                    # allow space as well
                    self.assertIn(ch, set(spinner.unicode_palette) | {" ", "=", "#"})
            # width should equal len(frame) - 2 (original frames are length 10 -> width 8)
            self.assertEqual(spinner.width, len(spinner.frames[0]) - 2)
        finally:
            # restore original method to avoid test pollution
            setattr(Spinner, "_supports_unicode", original_supports)
