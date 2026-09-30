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
        """Test that slimdown_html calls decompose on soup.img and removes non-href attributes."""
        from aider.scrape import slimdown_html

        class FakeTag:
            def __init__(self, name=None, attrs=None):
                self.name = name
                self.attrs = dict(attrs or {})
                self.decomposed = False

            def decompose(self):
                self.decomposed = True

            def __repr__(self):
                return f"<FakeTag {self.name} attrs={self.attrs} decomposed={self.decomposed}>"

        class FakeSoup:
            def __init__(self):
                # img should be truthy to trigger soup.img.decompose()
                self.img = FakeTag("img", {"src": "data", "alt": "an image"})
                # one svg to ensure svg branch runs
                self._svg = FakeTag("svg", {"id": "s"})
                # tags returned for find_all(True)
                self._all_tags = [
                    self.img,
                    FakeTag("a", {"href": "http://example.com", "title": "link"}),
                    FakeTag("p", {"class": "para", "href": "keep"}),
                    FakeTag("span", {"style": "color", "data-x": "1"}),  # no href -> will end up empty
                ]

            def find_all(self, *args, **kwargs):
                # mimic BeautifulSoup's find_all behavior for this function's usage
                if args and args[0] == "svg":
                    return [self._svg]
                if "href" in kwargs and callable(kwargs["href"]):
                    # return none matching data: hrefs for this test
                    return []
                if "src" in kwargs and callable(kwargs["src"]):
                    # return none matching data: srcs for this test
                    return []
                # find_all(True) -> return all tags
                if args and args[0] is True:
                    return list(self._all_tags)
                return []

        soup = FakeSoup()
        result = slimdown_html(soup)

        # Ensure returned object is our soup
        assert result is soup

        # svg should have been decomposed
        assert soup._svg.decomposed is True, "Expected svg.decompose() to be called"

        # target: img.decompose should have been called
        assert soup.img.decomposed is True, "Expected soup.img.decompose() to be called"

        # After slimming, tags should only retain 'href' attribute if present originally,
        # otherwise attrs should be emptied.
        # a tag: had href and title -> should keep only href
        a_tag = next(t for t in soup._all_tags if t.name == "a")
        assert "href" in a_tag.attrs and len(a_tag.attrs) == 1 and a_tag.attrs["href"] == "http://example.com"

        # p tag: had class and href -> should keep only href
        p_tag = next(t for t in soup._all_tags if t.name == "p")
        assert "href" in p_tag.attrs and len(p_tag.attrs) == 1 and p_tag.attrs["href"] == "keep"

        # span tag: had no href -> attrs should be empty
        span_tag = next(t for t in soup._all_tags if t.name == "span")
        assert span_tag.attrs == {}, "Expected non-href attributes to be removed"
