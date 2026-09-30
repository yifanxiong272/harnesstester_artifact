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
        """Test emphasize_header with various options to ensure the ': ' branch is taken and outputs match expectations."""
        # input with a colon+space so colon_position != -1
        text = "Title: rest"
        # default (HTML, no reference link)
        result_html = emphasize_header(text)
        expected_html = "<strong>Title:</strong><br> rest"
        self.assertEqual(result_html, expected_html)

        # markdown only, no reference link
        result_md = emphasize_header(text, only_markdown=True)
        expected_md = "**Title:**\n rest"
        self.assertEqual(result_md, expected_md)

        # HTML with reference link
        link = "http://example.com"
        result_html_link = emphasize_header(text, only_markdown=False, reference_link=link)
        expected_html_link = f"<strong><a href='{link}'>Title:</a></strong><br> rest"
        self.assertEqual(result_html_link, expected_html_link)

        # Markdown with reference link
        result_md_link = emphasize_header(text, only_markdown=True, reference_link=link)
        expected_md_link = f"[**Title:**]({link})\n rest"
        self.assertEqual(result_md_link, expected_md_link)

        # input without colon+space should return original string unchanged
        no_colon = "NoColonHere"
        result_no_colon = emphasize_header(no_colon)
        self.assertEqual(result_no_colon, no_colon)
