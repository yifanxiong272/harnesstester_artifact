import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.tools.pr_description')
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
        """Ensure list items are converted to <li> tokens (exercise saved-word branch)."""
        # Create a long list-like string so the function doesn't return early and processes list tokens
        long_words = "word " * 20  # makes the input length exceed the default x=70
        long_words2 = "another " * 20
        file_change_description = f"- {long_words.strip()}\n- {long_words2.strip()}"

        processed = insert_br_after_x_chars(file_change_description)

        # The result should be wrapped in a UL and contain two <li> tokens (one per list item)
        self.assertTrue(processed.startswith("<ul><li>"))
        self.assertIn("</ul>", processed)
        self.assertGreaterEqual(processed.count("<li>"), 2)
        # Also ensure there are <br> tokens somewhere (line breaks inserted/handled)
        self.assertIn("<br>", processed)
