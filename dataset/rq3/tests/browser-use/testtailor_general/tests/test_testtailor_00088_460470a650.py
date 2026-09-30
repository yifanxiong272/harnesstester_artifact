import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.dom.utils')
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
        """Test that cap_text_length truncates longer text and appends ellipsis."""
        # Standard truncation case: text longer than max_length
        text = "The quick brown fox jumps over the lazy dog"
        result = cap_text_length(text, 10)
        self.assertEqual(result, text[:10] + "...")

        # Edge case: max_length == 0 should return only the ellipsis
        result_zero = cap_text_length(text, 0)
        self.assertEqual(result_zero, "...")
        
        # Unicode / emoji handling: ensure slicing is character-based and ellipsis appended
        emoji_text = "😀😃😄😁😆"  # 5 characters
        result_emoji = cap_text_length(emoji_text, 3)
        self.assertEqual(result_emoji, emoji_text[:3] + "...")
