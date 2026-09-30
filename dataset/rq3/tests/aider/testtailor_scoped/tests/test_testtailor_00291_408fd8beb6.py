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
        """Ensure slimdown_html removes svg elements and strips non-href attributes from tags."""
        # Minimal fake soup/tag objects to exercise the target loop without external deps
        class FakeTag:
            def __init__(self, name, attrs=None):
                self.name = name
                self.attrs = dict(attrs or {})
                self.removed = False

            def decompose(self):
                self.removed = True

        class FakeSoup:
            def __init__(self, tags, img=None):
                self._tags = list(tags)
                # mimic BeautifulSoup's .img attribute access (None means no img)
                self.img = img

            def find_all(self, name=None, **kwargs):
                # emulate calls seen in slimdown_html:
                # - find_all("svg")
                # - find_all(href=...)
                # - find_all(src=...)
                # - find_all(True)
                if name == "svg":
                    return [t for t in self._tags if t.name == "svg" and not t.removed]
                if name is True:
                    return [t for t in self._tags if not t.removed]
                # For href/src searches, return empty list for simplicity
                if "href" in kwargs or "src" in kwargs:
                    return []
                return []

        # Build fake soup with one svg and one paragraph that has extra attrs
        svg_tag = FakeTag("svg", {"foo": "bar"})
        p_tag = FakeTag("p", {"class": "x", "href": "http://example.com", "data": "keep"})
        soup = FakeSoup([svg_tag, p_tag], img=None)

        # Call the function under test
        result = slimdown_html(soup)

        # svg must have been decomposed/removed
        self.assertTrue(svg_tag.removed, "SVG tag was not decomposed/removed")

        # Non-href attributes should be removed from remaining tags; href should be preserved
        self.assertIn("href", p_tag.attrs)
        self.assertEqual(p_tag.attrs, {"href": "http://example.com"})

        # The function should return the same soup object
        self.assertIs(result, soup)
