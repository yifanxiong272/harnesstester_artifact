import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.scrape')
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
        """Ensure tags with href starting with data: are removed by slimdown_html."""
        from bs4 import BeautifulSoup

        # Construct HTML containing a data: href link and a normal link with extra attributes.
        html = (
            '<div id="root">'
            '  <a href="data:image/png;base64,AAAA" id="inline" class="img">inline image</a>'
            '  <a href="http://example.com" data-extra="keepme" title="link">external</a>'
            '</div>'
        )
        soup = BeautifulSoup(html, "html.parser")

        # Run the function under test
        out = slimdown_html(soup)

        # The data: href link should be removed
        data_links = [t for t in out.find_all(href=True) if str(t.get("href", "")).startswith("data:")]
        self.assertEqual(len(data_links), 0, "data: href links should be decomposed/removed")

        # The normal external link should remain
        external = out.find(href="http://example.com")
        self.assertIsNotNone(external, "external link should remain")

        # All attributes except 'href' must be removed from remaining tags
        for tag in out.find_all(True):
            for attr in list(tag.attrs):
                self.assertEqual(attr, "href", f"Found unexpected attribute '{attr}' on tag {tag}")
