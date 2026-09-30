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
        """Ensure tags with src starting with data: are decomposed and attributes other than href are removed."""
        # Create lightweight mock soup/tag objects to avoid importing BeautifulSoup
        class MockTag:
            def __init__(self, name, attrs=None):
                self.name = name
                self.attrs = dict(attrs or {})
                self.removed = False

            def decompose(self):
                self.removed = True

            def __repr__(self):
                return f"<MockTag {self.name} id={self.attrs.get('id')} removed={self.removed}>"

        class MockSoup:
            def __init__(self, tags):
                # store tags in a list
                self._tags = list(tags)

            @property
            def img(self):
                for t in self._tags:
                    if not t.removed and t.name == "img":
                        return t
                return None

            def find_all(self, name=None, **kwargs):
                results = []
                for t in self._tags:
                    if t.removed:
                        continue
                    # handle name parameter
                    if name is True:
                        name_ok = True
                    elif isinstance(name, str):
                        name_ok = t.name == name
                    elif name is None:
                        name_ok = True
                    else:
                        name_ok = False

                    if not name_ok:
                        continue

                    # handle kwargs like href=lambda ...
                    ok = True
                    for key, cond in kwargs.items():
                        val = t.attrs.get(key)
                        try:
                            if not cond(val):
                                ok = False
                                break
                        except Exception:
                            ok = False
                            break
                    if ok:
                        results.append(t)
                return results

            def find(self, **kwargs):
                # support find by tag attributes (best-effort)
                for t in self._tags:
                    if t.removed:
                        continue
                    match = True
                    for k, v in kwargs.items():
                        if k == "id":
                            if t.attrs.get("id") != v:
                                match = False
                                break
                        else:
                            if t.attrs.get(k) != v:
                                match = False
                                break
                    if match:
                        return t
                return None

            def __repr__(self):
                return f"<MockSoup tags={self._tags}>"

        # Build tags reflecting the HTML used in the original failing test
        tags = [
            MockTag("div", {"id": "keep", "href": "https://example.com", "data-custom": "keepme", "title": "t"}),
            MockTag("script", {"id": "remove_script", "src": "data:text/javascript;base64,Zm9v"}),
            MockTag("iframe", {"id": "remove_iframe", "src": "data:text/html;base64,PGgxPkhlbGxvPC9oMT4="}),
            MockTag("img", {"id": "some_img", "src": "data:image/png;base64,iVBORw0KGgo="}),
            MockTag("a", {"id": "remove_link", "href": "data:text/plain;base64,SGVsbG8="}),
            MockTag("p", {"id": "stay", "class": "pclass"}),
            # include an svg to ensure that removal path is exercised
            MockTag("svg", {"id": "an_svg"}),
        ]
        # keep direct references to important tags for assertions after modification
        div_tag, script_tag, iframe_tag, img_tag, link_tag, p_tag, svg_tag = tags

        soup = MockSoup(tags)

        # Call the function under test
        result = slimdown_html(soup)

        # The function should have decomposed tags with src starting with data:
        self.assertTrue(script_tag.removed, "script with data: src should be decomposed")
        self.assertTrue(iframe_tag.removed, "iframe with data: src should be decomposed")

        # img should be removed by the earlier img-specific removal
        self.assertTrue(img_tag.removed, "img should be decomposed by img-specific removal")

        # link with href starting with data: should be removed by the href loop
        self.assertTrue(link_tag.removed, "tag with href starting with data: should be decomposed")

        # svg should be removed by the svg-specific removal
        self.assertTrue(svg_tag.removed, "svg tags should be decomposed")

        # The div with a normal href should remain (not decomposed)
        self.assertFalse(div_tag.removed, "div with normal href should not be decomposed")
        # After slimming, only the href attribute should remain
        self.assertEqual(set(div_tag.attrs.keys()), {"href"})
        self.assertEqual(div_tag.attrs.get("href"), "https://example.com")

        # Ensure other non-data elements remain but have had non-href attributes removed
        self.assertFalse(p_tag.removed, "non-data paragraph should not be decomposed")
        # paragraph had class attribute which should be removed (since it's not href)
        self.assertEqual(p_tag.attrs, {})
