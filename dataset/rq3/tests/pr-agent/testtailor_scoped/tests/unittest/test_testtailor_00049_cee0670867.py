import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.algo.utils')
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
        """Verify emphasize_header behavior for various combinations of flags/links and no-colon case"""
        text = "Header: rest"

        # Default (HTML, no reference link)
        out = emphasize_header(text)
        self.assertEqual(out, "<strong>Header:</strong><br> rest")

        # Markdown only, no reference link
        out_md = emphasize_header(text, only_markdown=True)
        self.assertEqual(out_md, "**Header:**\n rest")

        # HTML with reference link
        link = "http://example.com"
        out_html_link = emphasize_header(text, only_markdown=False, reference_link=link)
        self.assertEqual(out_html_link, "<strong><a href='http://example.com'>Header:</a></strong><br> rest")

        # Markdown with reference link
        out_md_link = emphasize_header(text, only_markdown=True, reference_link=link)
        self.assertEqual(out_md_link, "[**Header:**](http://example.com)\n rest")

        # Input with no ": " should be returned unchanged
        no_colon = "NoColonHere"
        self.assertEqual(emphasize_header(no_colon), no_colon)
