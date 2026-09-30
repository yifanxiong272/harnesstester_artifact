import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.scraper.browser.processing.html')
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
    def test_case_01(self):
        """Extract hyperlinks with absolute and relative URLs and nested tags"""
        html = """
        <html>
          <body>
            <a href="/about">About</a>
            <a href="contact.html">Contact</a>
            <a href="https://external.com/page">External</a>
            <a href="../up">Up One</a>
            <a href="section#1"><span>Section</span></a>
          </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        base_url = "https://example.com/dir/page.html"

        result = extract_hyperlinks(soup, base_url)

        expected = [
            ("About", "https://example.com/about"),
            ("Contact", "https://example.com/dir/contact.html"),
            ("External", "https://external.com/page"),
            ("Up One", "https://example.com/up"),
            ("Section", "https://example.com/dir/section#1"),
        ]

        self.assertEqual(result, expected)
