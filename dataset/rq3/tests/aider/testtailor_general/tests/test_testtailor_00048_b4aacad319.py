import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.search_replace')
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
        # prepare texts where original has an insertion ("brave ") so indices change
        search_text = "Hello world"
        replace_text = "Hello world"
        original_text = "Hello brave world"

        # simple patch-like object with the attributes used by map_patches
        class SimplePatch:
            def __init__(self, s1, s2, diffs):
                self.start1 = s1
                self.start2 = s2
                self.diffs = diffs

        # index of 'w' in "Hello world" is 6
        patch = SimplePatch(6, 6, [("=", "world")])

        # call function with debug True to hit the branch that writes tmp.html and calls dump()
        result = map_patches((search_text, replace_text, original_text), [patch], debug=True)

        # tmp.html should have been written and contain some HTML from diff_prettyHtml
        content = open("tmp.html", "r", encoding="utf-8").read()
        self.assertTrue(len(content) > 0)
        self.assertIn("<", content)  # crude check that it's HTML-like

        # The start1 should have been remapped to the index of "world" in original_text
        expected_index = original_text.index("world")
        self.assertEqual(result[0].start1, expected_index)
        self.assertEqual(result[0].start2, expected_index)

        # cleanup the temporary file
        __import__("os").remove("tmp.html")
