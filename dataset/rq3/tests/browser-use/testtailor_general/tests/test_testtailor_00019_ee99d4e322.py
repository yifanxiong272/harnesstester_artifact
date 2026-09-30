import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.browser.python_highlights')
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
        """Ensure get_cross_platform_font creates and caches a font under the ('system_font', size) key."""
        # Ensure a clean cache to start
        _FONT_CACHE.clear()

        # Prepare a sentinel object to be returned by the patched truetype
        sentinel_font = object()

        # Patch the truetype loader so it doesn't attempt to open real font files
        with unittest.mock.patch.object(ImageFont, "truetype", return_value=sentinel_font) as mock_truetype:
            # First call should load via ImageFont.truetype and store in cache
            result = get_cross_platform_font(16)
            self.assertIs(result, sentinel_font)

            cache_key = ("system_font", 16)
            # The cache must contain the key and the value must be our sentinel
            self.assertIn(cache_key, _FONT_CACHE)
            self.assertIs(_FONT_CACHE[cache_key], sentinel_font)

            # truetype should have been called exactly once for the initial load
            mock_truetype.assert_called_once()

            # Calling again with same size should return the cached object and not call truetype again
            result_again = get_cross_platform_font(16)
            self.assertIs(result_again, sentinel_font)
            mock_truetype.assert_called_once()  # still only one call overall
