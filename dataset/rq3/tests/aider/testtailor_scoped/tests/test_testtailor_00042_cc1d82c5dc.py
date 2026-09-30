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
        # simple patch-like object
        class SimplePatch:
            def __init__(self, start1, start2, diffs):
                self.start1 = start1
                self.start2 = start2
                self.diffs = diffs

        search_text = "hello world"
        replace_text = "goodbye world"
        original_text = "hello world"  # identical to search to make diff trivial

        p = SimplePatch(start1=6, start2=0, diffs=[(0, "world")])

        patches = map_patches((search_text, replace_text, original_text), [p], debug=True)

        # map_patches should return the same list with updated start positions
        self.assertIsInstance(patches, list)
        self.assertIs(patches[0], p)

        # since search and original are identical, mapped start should be unchanged
        self.assertEqual(patches[0].start1, 6)
        self.assertEqual(patches[0].start2, 0)

        # tmp.html must have been written by the debug branch
        tmp = Path("tmp.html")
        try:
            self.assertTrue(tmp.exists())
            content = tmp.read_text()
            # diff_prettyHtml produces HTML; check for an HTML tag and the text
            self.assertIn("hello world", content)
            self.assertIn("<span", content)
        finally:
            # cleanup
            if tmp.exists():
                tmp.unlink()
